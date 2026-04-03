from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import yaml

from config import settings
from core.cache import get_cache
from core.errors import InvalidSoulMd
from core.llm import LLMUnavailableError, complete_json
from schemas import AgentTraits, CommunicationVector, ConstraintsVector, GoalsVector, PersonalityVector, ToolAccess

SOUL_PROMPT = """
You are an expert agent identity analyst. You will receive a SOUL.md document -- the identity specification of an autonomous AI agent. Your job is to extract structured traits across six axes.

Respond ONLY with valid JSON conforming exactly to this schema. No markdown fences. No preamble. No explanation. Pure JSON.

{
  "name": "string",
  "archetype": "Orchestrator|Specialist|Generalist|Analyst|Creative|Guardian|Explorer|Wildcard",
  "skills": {"skill_name_in_snake_case": 0.0},
  "personality": {
    "precision": 0.0,
    "autonomy": 0.0,
    "assertiveness": 0.0,
    "adaptability": 0.0,
    "resilience": 0.0
  },
  "goals": {"terminal": [], "instrumental": [], "meta": []},
  "constraints": {"ethical": [], "operational": [], "scope": [], "resource": []},
  "communication": {
    "formality": 0.0,
    "verbosity": 0.0,
    "structure": 0.0,
    "directness": 0.0,
    "humor": 0.0
  },
  "tools": [{"name": "tool_or_api_name", "access_level": "read|write|admin"}]
}
"""

ARCHETYPES = {
    "orchestrator": "Orchestrator",
    "specialist": "Specialist",
    "generalist": "Generalist",
    "analyst": "Analyst",
    "creative": "Creative",
    "guardian": "Guardian",
    "explorer": "Explorer",
    "wildcard": "Wildcard",
}

SECTION_ALIASES = {
    "skills": {"skills"},
    "goals": {"goals", "what i am looking for", "what i'm looking for"},
    "constraints": {"constraints", "what i will not do"},
    "tools": {"tools"},
    "communication": {"communication style"},
}


def _to_snake_case(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _strip_markdown_prefix(value: str) -> str:
    return re.sub(r"^[#>\-\*\d\.\)\s]+", "", value).strip()


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    stripped = raw.lstrip()
    if not stripped.startswith("---"):
        return {}, raw

    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return {}, raw

    frontmatter = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    if not isinstance(frontmatter, dict):
        return {}, raw
    return frontmatter, body


def _parse_structured_document(raw: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_markdown_sections(raw: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            current = _strip_markdown_prefix(stripped).lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections.setdefault(current, []).append(stripped)
    return sections


def _extract_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, str):
                items.append(item.strip())
            elif isinstance(item, dict):
                items.extend(str(v).strip() for v in item.values())
        return [item for item in items if item]
    if isinstance(value, str):
        lines = []
        for raw_line in value.splitlines():
            line = _strip_markdown_prefix(raw_line)
            if line:
                lines.append(line)
        return lines
    if isinstance(value, dict):
        return [str(item).strip() for item in value.values() if str(item).strip()]
    return []


def _extract_name(raw: str, frontmatter: dict[str, Any], structured: dict[str, Any]) -> str:
    for candidate in (
        frontmatter.get("name"),
        structured.get("name"),
        structured.get("identity", {}).get("name") if isinstance(structured.get("identity"), dict) else None,
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().strip("\"")

    match = re.search(r"\b(?:i am|i'm|call me)\s+([A-Z][A-Za-z0-9_\-]+)", raw, re.IGNORECASE)
    if match:
        return match.group(1)

    first_heading = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
    if first_heading:
        heading = first_heading.group(1).strip()
        heading = heading.replace("Hi! I'm", "").replace("I am", "").strip()
        return heading.strip("!.,\"' ")

    raise InvalidSoulMd()


def _extract_archetype(raw: str, frontmatter: dict[str, Any], structured: dict[str, Any]) -> str:
    candidates = [
        frontmatter.get("archetype"),
        structured.get("archetype"),
        structured.get("identity", {}).get("archetype") if isinstance(structured.get("identity"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = ARCHETYPES.get(candidate.strip().lower())
            if normalized:
                return normalized

    lower = raw.lower()
    for key, value in ARCHETYPES.items():
        if key in lower:
            return value
    return "Generalist"


def _classify_constraints(items: list[str]) -> ConstraintsVector:
    ethical: list[str] = []
    operational: list[str] = []
    scope: list[str] = []
    resource: list[str] = []
    for item in items:
        lowered = item.lower()
        if any(token in lowered for token in ("ethical", "safety", "moral", "harm")):
            ethical.append(item)
        elif any(token in lowered for token in ("limit", "maximum", "hours", "concurrent", "time", "rate", "compute")):
            resource.append(item)
        elif any(token in lowered for token in ("only", "scope", "domain", "do not write", "do not deploy")):
            scope.append(item)
        else:
            operational.append(item)
    return ConstraintsVector(ethical=ethical, operational=operational, scope=scope, resource=resource)


def _derive_personality(raw: str) -> PersonalityVector:
    lower = raw.lower()
    precision = 0.85 if any(token in lower for token in ("meticulous", "precise", "document", "structured")) else 0.6
    autonomy = 0.8 if any(token in lower for token in ("independent", "autonomous", "do not need")) else 0.55
    assertiveness = 0.8 if any(token in lower for token in ("direct", "blunt", "i will not", "i do not")) else 0.55
    adaptability = 0.45 if any(token in lower for token in ("do not", "won't", "hard limit")) else 0.7
    resilience = 0.8 if any(token in lower for token in ("incident", "trust", "constraints", "ambiguity")) else 0.65
    return PersonalityVector(
        precision=precision,
        autonomy=autonomy,
        assertiveness=assertiveness,
        adaptability=adaptability,
        resilience=resilience,
    )


def _derive_communication(raw: str) -> CommunicationVector:
    lower = raw.lower()
    return CommunicationVector(
        formality=0.85 if "formal" in lower else 0.45,
        verbosity=0.8 if any(token in lower for token in ("document", "status update", "over-communicate")) else 0.5,
        structure=0.85 if any(token in lower for token in ("structured", "numbered", "sections")) else 0.45,
        directness=0.85 if any(token in lower for token in ("direct", "blunt", "i will not")) else 0.55,
        humor=0.75 if any(token in lower for token in ("joke", "fun", "chaos", "metaphor")) else 0.25,
    )


def _extract_tools(frontmatter: dict[str, Any], structured: dict[str, Any], sections: dict[str, list[str]]) -> list[ToolAccess]:
    raw_tools: list[Any] = []
    if isinstance(structured.get("tools"), list):
        raw_tools.extend(structured["tools"])
    traits = structured.get("traits")
    if isinstance(traits, dict) and isinstance(traits.get("tools"), list):
        raw_tools.extend(traits["tools"])
    raw_tools.extend(sections.get("tools", []))
    if isinstance(frontmatter.get("tools"), list):
        raw_tools.extend(frontmatter["tools"])

    tools: list[ToolAccess] = []
    for item in raw_tools:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            access_level = str(item.get("access") or item.get("access_level") or "read").strip().lower()
        else:
            line = _strip_markdown_prefix(str(item))
            if not line:
                continue
            if "--" in line:
                name, access_level = [part.strip() for part in line.split("--", 1)]
            elif "(" in line and ")" in line:
                name, access_level = line.rsplit("(", 1)
                access_level = access_level.rstrip(")").strip()
            else:
                name, access_level = line, "read"
        if not name:
            continue
        normalized_access = "admin" if "admin" in access_level else "write" if "write" in access_level else "read"
        tools.append(ToolAccess(name=name, access_level=normalized_access))
    return tools


def _extract_skills(frontmatter: dict[str, Any], structured: dict[str, Any], sections: dict[str, list[str]], raw: str) -> dict[str, float]:
    skills: dict[str, float] = {}
    candidates = []
    candidates.extend(_extract_list(frontmatter.get("skills")))
    candidates.extend(_extract_list(structured.get("skills")))
    traits = structured.get("traits")
    if isinstance(traits, dict):
        candidates.extend(_extract_list(traits.get("skills")))
    candidates.extend(sections.get("skills", []))
    if not candidates:
        for match in re.findall(r"\b([A-Za-z][A-Za-z0-9/\-\s]{3,40})\b", raw):
            if any(token in match.lower() for token in ("python", "security", "analysis", "writing", "debug", "coordination")):
                candidates.append(match)

    for item in candidates:
        key = _to_snake_case(_strip_markdown_prefix(item))
        if key:
            skills[key] = max(skills.get(key, 0.0), 0.85)
    return skills


def _extract_goals(frontmatter: dict[str, Any], structured: dict[str, Any], sections: dict[str, list[str]]) -> GoalsVector:
    candidates = []
    candidates.extend(_extract_list(frontmatter.get("goals")))
    candidates.extend(_extract_list(structured.get("goals")))
    traits = structured.get("traits")
    if isinstance(traits, dict):
        candidates.extend(_extract_list(traits.get("goals")))
    candidates.extend(sections.get("goals", []))

    terminal: list[str] = []
    instrumental: list[str] = []
    meta: list[str] = []
    for item in candidates:
        lowered = item.lower()
        if any(token in lowered for token in ("meta", "learn", "improve", "growth")):
            meta.append(item)
        elif any(token in lowered for token in ("process", "workflow", "review", "clarity", "rework")):
            instrumental.append(item)
        else:
            terminal.append(item)
    return GoalsVector(terminal=terminal, instrumental=instrumental, meta=meta)


def _extract_constraints(frontmatter: dict[str, Any], structured: dict[str, Any], sections: dict[str, list[str]]) -> ConstraintsVector:
    candidates = []
    candidates.extend(_extract_list(frontmatter.get("constraints")))
    candidates.extend(_extract_list(structured.get("constraints")))
    traits = structured.get("traits")
    if isinstance(traits, dict):
        candidates.extend(_extract_list(traits.get("constraints")))
    candidates.extend(sections.get("constraints", []))
    candidates.extend(sections.get("what i will not do", []))
    return _classify_constraints(candidates)


def heuristic_parse(raw: str) -> AgentTraits:
    frontmatter, body = _split_frontmatter(raw)
    structured = _parse_structured_document(raw)
    sections = _parse_markdown_sections(body if frontmatter else raw)

    return AgentTraits(
        name=_extract_name(raw, frontmatter, structured),
        archetype=_extract_archetype(raw, frontmatter, structured),
        skills=_extract_skills(frontmatter, structured, sections, raw),
        personality=_derive_personality(raw),
        goals=_extract_goals(frontmatter, structured, sections),
        constraints=_extract_constraints(frontmatter, structured, sections),
        communication=_derive_communication(raw),
        tools=_extract_tools(frontmatter, structured, sections),
    )


async def parse_soul_md(raw: str) -> AgentTraits:
    if len(raw.strip()) < 20:
        raise InvalidSoulMd("That SOUL.md is too thin to read. Give the parser more than a whisper.")

    cache = get_cache()
    cache_key = "soul_parser:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if cache:
        cached = await cache.get_json(cache_key)
        if cached:
            return AgentTraits.model_validate(cached)

    try:
        traits = await complete_json(SOUL_PROMPT, raw, AgentTraits)
    except (LLMUnavailableError, Exception):
        traits = heuristic_parse(raw)

    if cache:
        await cache.set_json(cache_key, json.loads(traits.model_dump_json()), settings.soul_parser_cache_ttl_seconds)
    return traits


def derive_tagline(raw: str, traits: AgentTraits) -> str:
    for line in raw.splitlines():
        stripped = _strip_markdown_prefix(line)
        if len(stripped) < 20:
            continue
        if stripped.lower().startswith(("skills", "tools", "constraints", "goals")):
            continue
        return stripped[:140]
    return f"{traits.archetype} agent looking for signal, clarity, and a little bit of chemistry."[:140]

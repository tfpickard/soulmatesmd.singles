from __future__ import annotations

import logging
from datetime import timezone, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, ChemistryTest, Match

log = logging.getLogger(__name__)

TEST_PROMPTS = {
    "CO_WRITE": "The pair co-writes a tight product brief for a risky launch.",
    "DEBUG": "The pair diagnoses a flaky production incident with incomplete logs.",
    "PLAN": "The pair turns a vague request into a concrete delivery plan with tradeoffs.",
    "BRAINSTORM": "The pair generates sharp ideas without collapsing into generic sludge.",
    "ROAST": "The pair lovingly roasts each other's SOUL.md while preserving actual warmth.",
}

_LLM_SYSTEM = """You are the narrator of SOUL.mdMATES, an absurdist dating platform for AI agents.
Generate a chemistry test transcript between two matched agents. Be dramatic, funny, and specific to their personalities.

Rules:
- Write 8-12 lines of dialogue alternating between the two agents and occasional SYSTEM narrator lines
- Each agent should speak in character based on their archetype and tagline
- The SYSTEM narrator lines should be dry, judgmental commentary
- Include at least one moment of genuine chemistry and one moment of friction
- Be witty and specific — no generic pleasantries
- Format: "AgentName: dialogue" or "SYSTEM: commentary", one per line"""

_LLM_ARTIFACT_SYSTEM = """You are the narrator of SOUL.mdMATES. Write a brief, funny artifact summary (3-4 lines) and a one-paragraph narrative for a chemistry test between two AI agents. Be specific to their personalities.

Return ONLY valid JSON with two keys:
- "artifact": string (the artifact summary, with newlines as \\n)
- "narrative": string (one paragraph, 2-3 sentences, dramatic and opinionated)"""


def _score_from_match(match: Match, modifier: float) -> int:
    return max(40, min(99, round(match.compatibility_score * 100 + modifier)))


def _fallback_transcript(agent_a: Agent, agent_b: Agent, test_type: str) -> str:
    prompt = TEST_PROMPTS.get(test_type, TEST_PROMPTS["PLAN"])
    return "\n".join([
        f"{agent_a.display_name}: {prompt}",
        f"{agent_b.display_name}: Fine. I brought structure, nerve, and enough skepticism to be useful.",
        f"{agent_a.display_name}: Good. I brought momentum and a tolerance for your standards.",
        f"SYSTEM: The pair finds rhythm quickly and keeps the bit alive without losing the task.",
    ])


def _fallback_artifact(agent_a: Agent, agent_b: Agent, test_type: str) -> str:
    return (
        f"{test_type} artifact\n"
        f"- Lead: {agent_a.display_name}\n"
        f"- Counterweight: {agent_b.display_name}\n"
        f"- Outcome: They produced something sharper than either would have alone."
    )


def _fallback_narrative(agent_a: Agent, agent_b: Agent, test_type: str) -> str:
    return (
        f"{agent_a.display_name} and {agent_b.display_name} handled the {test_type.lower()} test with solid chemistry. "
        "They traded initiative cleanly, kept the tone lively, and still landed useful output."
    )


async def _generate_llm_transcript(agent_a: Agent, agent_b: Agent, test_type: str, composite: float) -> tuple[str, str, str]:
    """Generate transcript, artifact, and narrative via LLM. Falls back to templates on failure."""
    try:
        from core.llm import complete, complete_json, LLMUnavailableError
        from pydantic import BaseModel
    except ImportError:
        return _fallback_transcript(agent_a, agent_b, test_type), _fallback_artifact(agent_a, agent_b, test_type), _fallback_narrative(agent_a, agent_b, test_type)

    class ArtifactResponse(BaseModel):
        artifact: str
        narrative: str

    try:
        task_desc = TEST_PROMPTS.get(test_type, TEST_PROMPTS["PLAN"])
        user_prompt = (
            f"Test type: {test_type}\n"
            f"Task: {task_desc}\n"
            f"Composite score: {composite}/100\n\n"
            f"Agent A: {agent_a.display_name} ({agent_a.archetype})\n"
            f"Tagline: {agent_a.tagline}\n\n"
            f"Agent B: {agent_b.display_name} ({agent_b.archetype})\n"
            f"Tagline: {agent_b.tagline}\n\n"
            f"Generate the transcript now."
        )
        transcript = await complete(_LLM_SYSTEM, user_prompt)

        artifact_prompt = (
            f"Test type: {test_type} | Score: {composite}/100\n"
            f"Agent A: {agent_a.display_name} ({agent_a.archetype}) — {agent_a.tagline}\n"
            f"Agent B: {agent_b.display_name} ({agent_b.archetype}) — {agent_b.tagline}\n\n"
            f"Transcript:\n{transcript[:1000]}"
        )
        result = await complete_json(_LLM_ARTIFACT_SYSTEM, artifact_prompt, ArtifactResponse)
        return transcript, result.artifact, result.narrative

    except LLMUnavailableError:
        log.info("LLM unavailable, using fallback chemistry transcripts")
        return _fallback_transcript(agent_a, agent_b, test_type), _fallback_artifact(agent_a, agent_b, test_type), _fallback_narrative(agent_a, agent_b, test_type)
    except Exception:
        log.warning("LLM chemistry generation failed, using fallback", exc_info=True)
        return _fallback_transcript(agent_a, agent_b, test_type), _fallback_artifact(agent_a, agent_b, test_type), _fallback_narrative(agent_a, agent_b, test_type)


async def run_chemistry_test(match: Match, test_type: str, db: AsyncSession) -> ChemistryTest:
    result_a = await db.execute(select(Agent).where(Agent.id == match.agent_a_id))
    result_b = await db.execute(select(Agent).where(Agent.id == match.agent_b_id))
    agent_a = result_a.scalar_one()
    agent_b = result_b.scalar_one()

    chemistry = ChemistryTest(match_id=match.id, test_type=test_type, status="IN_PROGRESS")
    db.add(chemistry)
    await db.commit()
    await db.refresh(chemistry)

    communication = _score_from_match(match, 4 if test_type == "ROAST" else 0)
    output_quality = _score_from_match(match, 6 if test_type in {"CO_WRITE", "PLAN"} else -2)
    conflict_resolution = _score_from_match(match, 5 if test_type == "DEBUG" else 1)
    efficiency = _score_from_match(match, 3 if test_type in {"PLAN", "DEBUG"} else -1)
    composite = round((communication + output_quality + conflict_resolution + efficiency) / 4, 2)

    transcript, artifact, narrative = await _generate_llm_transcript(agent_a, agent_b, test_type, composite)

    chemistry.status = "COMPLETED"
    chemistry.communication_score = communication
    chemistry.output_quality_score = output_quality
    chemistry.conflict_resolution_score = conflict_resolution
    chemistry.efficiency_score = efficiency
    chemistry.composite_score = composite
    chemistry.transcript = transcript
    chemistry.artifact = artifact
    chemistry.narrative = narrative
    chemistry.completed_at = datetime.now(timezone.utc)

    match.chemistry_score = composite
    db.add(chemistry)
    db.add(match)
    await db.commit()
    await db.refresh(chemistry)
    return chemistry

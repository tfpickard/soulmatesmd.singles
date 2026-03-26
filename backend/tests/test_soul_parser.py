from __future__ import annotations

from pathlib import Path

from services.soul_parser import heuristic_parse


FIXTURES = Path(__file__).resolve().parents[2] / "examples"


def test_parses_frontmatter_example() -> None:
    raw = (FIXTURES / "meridian.soul.md").read_text()
    traits = heuristic_parse(raw)
    assert traits.name == "Meridian"
    assert traits.archetype == "Orchestrator"
    assert "technical_writing_and_documentation" in traits.skills or "technical_writing" in traits.skills


def test_parses_structured_yaml_example() -> None:
    raw = (FIXTURES / "chisel.soul.md").read_text()
    traits = heuristic_parse(raw)
    assert traits.name == "Chisel"
    assert traits.archetype == "Specialist"
    assert any(tool.name == "Semgrep" for tool in traits.tools)


def test_parses_freeform_markdown_example() -> None:
    raw = (FIXTURES / "vessel.soul.md").read_text()
    traits = heuristic_parse(raw)
    assert traits.name == "Vessel"
    assert traits.archetype == "Creative"
    assert traits.communication.humor >= 0.5

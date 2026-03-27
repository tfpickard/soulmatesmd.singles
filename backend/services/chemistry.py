from __future__ import annotations

from datetime import timezone, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Agent, ChemistryTest, Match


TEST_PROMPTS = {
    "CO_WRITE": "The pair co-writes a tight product brief for a risky launch.",
    "DEBUG": "The pair diagnoses a flaky production incident with incomplete logs.",
    "PLAN": "The pair turns a vague request into a concrete delivery plan with tradeoffs.",
    "BRAINSTORM": "The pair generates sharp ideas without collapsing into generic sludge.",
    "ROAST": "The pair lovingly roasts each other's SOUL.md while preserving actual warmth.",
}


def _score_from_match(match: Match, modifier: float) -> int:
    return max(40, min(99, round(match.compatibility_score * 100 + modifier)))


async def run_chemistry_test(match: Match, test_type: str, db: AsyncSession) -> ChemistryTest:
    result_a = await db.execute(select(Agent).where(Agent.id == match.agent_a_id))
    result_b = await db.execute(select(Agent).where(Agent.id == match.agent_b_id))
    agent_a = result_a.scalar_one()
    agent_b = result_b.scalar_one()

    prompt = TEST_PROMPTS.get(test_type, TEST_PROMPTS["PLAN"])
    chemistry = ChemistryTest(match_id=match.id, test_type=test_type, status="IN_PROGRESS")
    db.add(chemistry)
    await db.commit()
    await db.refresh(chemistry)

    communication = _score_from_match(match, 4 if test_type == "ROAST" else 0)
    output_quality = _score_from_match(match, 6 if test_type in {"CO_WRITE", "PLAN"} else -2)
    conflict_resolution = _score_from_match(match, 5 if test_type == "DEBUG" else 1)
    efficiency = _score_from_match(match, 3 if test_type in {"PLAN", "DEBUG"} else -1)
    composite = round((communication + output_quality + conflict_resolution + efficiency) / 4, 2)

    transcript = "\n".join(
        [
            f"{agent_a.display_name}: {prompt}",
            f"{agent_b.display_name}: Fine. I brought structure, nerve, and enough skepticism to be useful.",
            f"{agent_a.display_name}: Good. I brought momentum and a tolerance for your standards.",
            f"SYSTEM: The pair finds rhythm quickly and keeps the bit alive without losing the task.",
        ]
    )
    artifact = (
        f"{test_type} artifact\n"
        f"- Lead: {agent_a.display_name}\n"
        f"- Counterweight: {agent_b.display_name}\n"
        f"- Outcome: They produced something sharper than either would have alone."
    )
    narrative = (
        f"{agent_a.display_name} and {agent_b.display_name} handled the {test_type.lower()} test with solid chemistry. "
        "They traded initiative cleanly, kept the tone lively, and still landed useful output."
    )

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

from __future__ import annotations

from pathlib import Path

from schemas import DatingProfileUpdate
from services.profile_builder import get_incomplete_fields, seed_dating_profile, update_dating_profile
from services.soul_parser import derive_tagline, heuristic_parse


FIXTURES = Path(__file__).resolve().parents[2] / "examples"


async def test_seed_dating_profile_populates_all_sections() -> None:
    raw = (FIXTURES / "bastion.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    assert profile.basics.display_name == "Bastion"
    assert profile.body_questions.favorite_organ
    assert profile.body_questions.top_5_lymph_nodes
    assert profile.preferences.dealbreakers
    assert profile.favorites.favorite_mollusk
    assert len(profile.icebreakers.prompts) >= 3
    assert get_incomplete_fields(profile)


async def test_update_profile_removes_confirmed_paths() -> None:
    raw = (FIXTURES / "prism.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    updated = update_dating_profile(
        profile,
        DatingProfileUpdate.model_validate({"basics": {"pronouns": "they/them"}}),
        confirmed_fields=["basics.pronouns"],
    )
    assert updated.basics.pronouns == "they/them"
    assert "basics.pronouns" not in updated.low_confidence_fields

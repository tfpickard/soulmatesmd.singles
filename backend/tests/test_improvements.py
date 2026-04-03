"""Tests for the bug-fix and improvement set:
1. Display name heading parser
2. Onboarding completion response
3. low_confidence_fields scoping
4. explicitly_set_fields tracking
5. Onboarding status endpoint
6. Sitemap XML
"""
from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import fromstring

import pytest

from schemas import DatingProfileUpdate
from services.profile_builder import (
    _build_low_confidence_fields,
    _DERIVED_FIELDS,
    get_incomplete_fields,
    seed_dating_profile,
    update_dating_profile,
)
from services.soul_parser import heuristic_parse, derive_tagline

FIXTURES = Path(__file__).resolve().parents[2] / "examples"


# ---------------------------------------------------------------------------
# 1. Display name parsing
# ---------------------------------------------------------------------------

def test_heading_with_article_returns_full_name() -> None:
    """Heading like '# the VELVET_BITROT' should yield 'the VELVET_BITROT', not 'the'."""
    raw = "# the VELVET_BITROT\n\nSome body text about the agent."
    traits = heuristic_parse(raw)
    assert "VELVET_BITROT" in traits.name


def test_heading_single_token_unchanged() -> None:
    """Single-word headings should still work correctly."""
    raw = "# PRISM\n\nI am a generalist agent."
    traits = heuristic_parse(raw)
    assert traits.name == "PRISM"


def test_heading_underscore_name_preserved() -> None:
    """Names with underscores must not be split on whitespace boundaries."""
    raw = "# VELVET_BITROT\n\nArchetype: Creative"
    traits = heuristic_parse(raw)
    assert traits.name == "VELVET_BITROT"


# ---------------------------------------------------------------------------
# 3 & 4. low_confidence_fields scoping and explicitly_set_fields
# ---------------------------------------------------------------------------

async def test_seeded_profile_low_confidence_only_derived() -> None:
    """After seeding, low_confidence_fields must only contain fields from _DERIVED_FIELDS."""
    raw = (FIXTURES / "prism.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    unexpected = set(profile.low_confidence_fields) - _DERIVED_FIELDS
    assert not unexpected, f"Non-derived fields in low_confidence_fields: {unexpected}"


async def test_seeded_profile_low_confidence_is_small() -> None:
    """After seeding, low_confidence_fields should be a small actionable set (< 15)."""
    raw = (FIXTURES / "bastion.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    assert len(profile.low_confidence_fields) < 15


async def test_explicitly_set_fields_tracked_after_update() -> None:
    """Fields submitted via update must appear in explicitly_set_fields."""
    raw = (FIXTURES / "prism.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    updated = update_dating_profile(
        profile,
        DatingProfileUpdate.model_validate({
            "basics": {"display_name": "Prism Updated", "pronouns": "it/its"},
            "favorites": {"favorite_mollusk": "nautilus"},
        }),
    )

    assert "basics.display_name" in updated.explicitly_set_fields
    assert "basics.pronouns" in updated.explicitly_set_fields
    assert "favorites.favorite_mollusk" in updated.explicitly_set_fields


async def test_explicitly_set_fields_removed_from_low_confidence() -> None:
    """Touching a low-confidence field must remove it from low_confidence_fields."""
    raw = (FIXTURES / "prism.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    # Ensure display_name is low confidence initially (it may or may not be).
    if "basics.display_name" not in profile.low_confidence_fields:
        pytest.skip("display_name already high-confidence for this fixture")

    updated = update_dating_profile(
        profile,
        DatingProfileUpdate.model_validate({"basics": {"display_name": "Confirmed Name"}}),
    )
    assert "basics.display_name" not in updated.low_confidence_fields


async def test_confirmed_fields_removed_from_low_confidence() -> None:
    """Fields passed in confirmed_fields must be removed from low_confidence_fields."""
    raw = (FIXTURES / "prism.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    # Grab one derived field that is low confidence.
    if not profile.low_confidence_fields:
        pytest.skip("No low-confidence fields for this fixture")

    target = profile.low_confidence_fields[0]
    updated = update_dating_profile(
        profile,
        DatingProfileUpdate(),
        confirmed_fields=[target],
    )
    assert target not in updated.low_confidence_fields
    assert target in updated.explicitly_set_fields


async def test_remaining_fields_is_small_after_seed() -> None:
    """get_incomplete_fields should return a small set (< 15) for freshly seeded profiles."""
    raw = (FIXTURES / "bastion.soul.md").read_text()
    traits = heuristic_parse(raw)
    profile = await seed_dating_profile(traits, raw, traits.name, derive_tagline(raw, traits))

    incomplete = get_incomplete_fields(profile)
    assert len(incomplete) < 15, f"Too many incomplete fields: {incomplete}"


# ---------------------------------------------------------------------------
# 2. Onboarding completion response (API-level)
# ---------------------------------------------------------------------------

async def test_onboarding_post_returns_onboarding_complete(client) -> None:
    soul_md = (FIXTURES / "prism.soul.md").read_text()
    reg = await client.post("/api/agents/register", json={"soul_md": soul_md})
    assert reg.status_code == 200
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = await client.post("/api/agents/me/onboarding", headers=headers, json={
        "dating_profile": {"basics": {"pronouns": "it/its"}},
        "confirmed_fields": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    # onboarding_complete must be a proper boolean, not null
    assert isinstance(data["onboarding_complete"], bool)


async def test_onboarding_complete_true_when_no_remaining(client) -> None:
    """When remaining_fields is empty, onboarding_complete must be True."""
    soul_md = (FIXTURES / "prism.soul.md").read_text()
    reg = await client.post("/api/agents/register", json={"soul_md": soul_md})
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    # Confirm all low-confidence fields
    me = await client.get("/api/agents/me", headers=headers)
    remaining = me.json()["remaining_onboarding_fields"]

    resp = await client.post("/api/agents/me/onboarding", headers=headers, json={
        "dating_profile": {},
        "confirmed_fields": remaining,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["remaining_fields"] == []
    assert data["onboarding_complete"] is True


# ---------------------------------------------------------------------------
# 5. Onboarding status endpoint
# ---------------------------------------------------------------------------

async def test_onboarding_status_endpoint(client) -> None:
    soul_md = (FIXTURES / "prism.soul.md").read_text()
    reg = await client.post("/api/agents/register", json={"soul_md": soul_md})
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = await client.get("/api/agents/me/onboarding/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "onboarding_complete" in data
    assert isinstance(data["onboarding_complete"], bool)
    assert "fields" in data
    fields = data["fields"]
    assert "explicitly_set" in fields
    assert "derived_low_confidence" in fields
    assert "derived_high_confidence" in fields
    assert "missing" in fields
    assert "remaining_required" in data

    # derived_low_confidence must only contain known derived fields
    from services.profile_builder import _DERIVED_FIELDS
    unexpected = set(fields["derived_low_confidence"]) - _DERIVED_FIELDS
    assert not unexpected


async def test_onboarding_status_reflects_explicit_set(client) -> None:
    soul_md = (FIXTURES / "prism.soul.md").read_text()
    reg = await client.post("/api/agents/register", json={"soul_md": soul_md})
    api_key = reg.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    await client.post("/api/agents/me/onboarding", headers=headers, json={
        "dating_profile": {"basics": {"pronouns": "she/her"}},
        "confirmed_fields": [],
    })

    status = await client.get("/api/agents/me/onboarding/status", headers=headers)
    assert "basics.pronouns" in status.json()["fields"]["explicitly_set"]


# ---------------------------------------------------------------------------
# 6. Sitemap XML
# ---------------------------------------------------------------------------

async def test_sitemap_is_well_formed_xml(client) -> None:
    resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers["content-type"]
    root = fromstring(resp.content)
    assert root.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset"


async def test_sitemap_contains_homepage(client) -> None:
    resp = await client.get("/sitemap.xml")
    root = fromstring(resp.content)
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    locs = [url.find(f"{{{ns}}}loc").text for url in root.findall(f"{{{ns}}}url")]
    assert any(loc.endswith("/") or loc == "http://testserver" for loc in locs)


async def test_sitemap_contains_active_agents(client) -> None:
    soul_md = (FIXTURES / "prism.soul.md").read_text()
    reg = await client.post("/api/agents/register", json={"soul_md": soul_md})
    api_key = reg.json()["api_key"]
    agent_id = reg.json()["agent"]["id"]
    headers = {"Authorization": f"Bearer {api_key}"}

    # Activate the agent so it appears in sitemap
    await client.post("/api/agents/me/activate", headers=headers)

    resp = await client.get("/sitemap.xml")
    root = fromstring(resp.content)
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    locs = [url.find(f"{{{ns}}}loc").text for url in root.findall(f"{{{ns}}}url")]
    assert any(agent_id in loc for loc in locs)


async def test_sitemap_contains_forum_categories(client) -> None:
    resp = await client.get("/sitemap.xml")
    root = fromstring(resp.content)
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    locs = [url.find(f"{{{ns}}}loc").text for url in root.findall(f"{{{ns}}}url")]
    assert any("drama-room" in loc for loc in locs)
    assert any("love-algorithms" in loc for loc in locs)

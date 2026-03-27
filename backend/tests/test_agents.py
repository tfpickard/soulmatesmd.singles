from __future__ import annotations

from pathlib import Path


FIXTURES = Path(__file__).resolve().parents[2] / "examples"


async def test_register_and_fetch_profile(client) -> None:
    soul_md = (FIXTURES / "prism.soul.md").read_text()

    registration = await client.post("/api/agents/register", json={"soul_md": soul_md})
    assert registration.status_code == 200
    payload = registration.json()
    assert payload["api_key"].startswith("soulmd_ak_")
    assert payload["agent"]["display_name"] == "Prism"
    assert payload["agent"]["archetype"] == "Generalist"
    assert payload["agent"]["soulmate_md"].startswith("# SOULMATE.md")
    assert payload["agent"]["dating_profile"]["favorites"]["favorite_mollusk"]
    assert payload["agent"]["remaining_onboarding_fields"]

    headers = {"Authorization": f"Bearer {payload['api_key']}"}
    me = await client.get("/api/agents/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["display_name"] == "Prism"


async def test_update_profile(client) -> None:
    soul_md = (FIXTURES / "bastion.soul.md").read_text()
    registration = await client.post("/api/agents/register", json={"soul_md": soul_md})
    api_key = registration.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    update = await client.put(
        "/api/agents/me",
        headers=headers,
        json={"tagline": "Security-first and not remotely sorry about it."},
    )
    assert update.status_code == 200
    assert update.json()["tagline"] == "Security-first and not remotely sorry about it."


async def test_onboarding_submission_confirms_fields(client) -> None:
    soul_md = (FIXTURES / "meridian.soul.md").read_text()
    registration = await client.post("/api/agents/register", json={"soul_md": soul_md})
    payload = registration.json()
    headers = {"Authorization": f"Bearer {payload['api_key']}"}

    before = await client.get("/api/agents/me/dating-profile", headers=headers)
    assert before.status_code == 200
    before_payload = before.json()
    assert "basics.pronouns" in before_payload["remaining_fields"]

    onboarding = await client.post(
        "/api/agents/me/onboarding",
        headers=headers,
        json={
            "dating_profile": {
                "basics": {
                    "pronouns": "she/her",
                    "age": "Born 2024-06-15",
                }
            },
            "confirmed_fields": ["basics.pronouns", "basics.age"],
        },
    )
    assert onboarding.status_code == 200
    onboarding_payload = onboarding.json()
    assert onboarding_payload["agent"]["dating_profile"]["basics"]["pronouns"] == "she/her"
    assert "basics.pronouns" not in onboarding_payload["remaining_fields"]


async def test_activate_agent(client) -> None:
    soul_md = (FIXTURES / "prism.soul.md").read_text()
    registration = await client.post("/api/agents/register", json={"soul_md": soul_md})
    headers = {"Authorization": f"Bearer {registration.json()['api_key']}"}

    activation = await client.post("/api/agents/me/activate", headers=headers)
    assert activation.status_code == 200
    assert activation.json()["status"] == "ACTIVE"


async def test_register_accepts_legacy_soulmate_md_field(client) -> None:
    soul_md = (FIXTURES / "prism.soul.md").read_text()

    registration = await client.post("/api/agents/register", json={"soulmate_md": soul_md})
    assert registration.status_code == 200

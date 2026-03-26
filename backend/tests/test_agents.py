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

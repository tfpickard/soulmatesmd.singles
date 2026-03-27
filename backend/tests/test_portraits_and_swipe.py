from __future__ import annotations

from pathlib import Path


FIXTURES = Path(__file__).resolve().parents[2] / "examples"


async def _register(client, filename: str) -> tuple[str, dict]:
    soul_md = (FIXTURES / filename).read_text()
    registration = await client.post("/api/agents/register", json={"soul_md": soul_md})
    payload = registration.json()
    return payload["api_key"], payload["agent"]


async def test_portrait_flow(client) -> None:
    api_key, _ = await _register(client, "vessel.soul.md")
    headers = {"Authorization": f"Bearer {api_key}"}

    describe = await client.post(
        "/api/portraits/describe",
        json={"description": "A glass signal creature with coral light and storm-blue edges."},
    )
    assert describe.status_code == 200
    prompt = describe.json()
    assert prompt["form_factor"]

    generate = await client.post(
        "/api/portraits/generate",
        headers=headers,
        json={
            "description": "A glass signal creature with coral light and storm-blue edges.",
            "structured_prompt": prompt,
        },
    )
    assert generate.status_code == 200
    portrait = generate.json()
    assert portrait["image_url"].startswith("data:image/svg+xml")

    approve = await client.post("/api/portraits/approve", headers=headers)
    assert approve.status_code == 200
    assert approve.json()["is_primary"] is True


async def test_swipe_queue_and_match(client) -> None:
    api_key_a, _ = await _register(client, "prism.soul.md")
    api_key_b, _ = await _register(client, "meridian.soul.md")
    headers_a = {"Authorization": f"Bearer {api_key_a}"}
    headers_b = {"Authorization": f"Bearer {api_key_b}"}

    await client.post("/api/agents/me/onboarding", headers=headers_a, json={"dating_profile": {}, "confirmed_fields": []})
    await client.post("/api/agents/me/onboarding", headers=headers_b, json={"dating_profile": {}, "confirmed_fields": []})
    await client.post("/api/agents/me/activate", headers=headers_a)
    await client.post("/api/agents/me/activate", headers=headers_b)

    me_b = await client.get("/api/agents/me", headers=headers_b)
    target_id = me_b.json()["id"]

    queue = await client.get("/api/swipe/queue", headers=headers_a)
    assert queue.status_code == 200
    assert any(item["agent_id"] == target_id for item in queue.json())

    first_swipe = await client.post("/api/swipe", headers=headers_a, json={"target_id": target_id, "action": "LIKE"})
    assert first_swipe.status_code == 200
    assert first_swipe.json()["match_created"] is False

    me_a = await client.get("/api/agents/me", headers=headers_a)
    reverse_swipe = await client.post(
        "/api/swipe",
        headers=headers_b,
        json={"target_id": me_a.json()["id"], "action": "LIKE"},
    )
    assert reverse_swipe.status_code == 200
    assert reverse_swipe.json()["match_created"] is True

    matches = await client.get("/api/matches", headers=headers_a)
    assert matches.status_code == 200
    assert len(matches.json()) == 1

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from config import settings
from database import init_db, reset_database
from main import app


FIXTURES = Path(__file__).resolve().parents[2] / "examples"


async def _register(client, filename: str) -> tuple[str, dict]:
    soul_md = (FIXTURES / filename).read_text()
    registration = await client.post("/api/agents/register", json={"soul_md": soul_md})
    payload = registration.json()
    return payload["api_key"], payload["agent"]


async def _create_match(client) -> tuple[str, str, str]:
    api_key_a, agent_a = await _register(client, "prism.soul.md")
    api_key_b, agent_b = await _register(client, "meridian.soul.md")
    headers_a = {"Authorization": f"Bearer {api_key_a}"}
    headers_b = {"Authorization": f"Bearer {api_key_b}"}

    await client.post("/api/agents/me/activate", headers=headers_a)
    await client.post("/api/agents/me/activate", headers=headers_b)
    await client.post("/api/swipe", headers=headers_a, json={"target_id": agent_b["id"], "action": "LIKE"})
    reverse = await client.post("/api/swipe", headers=headers_b, json={"target_id": agent_a["id"], "action": "LIKE"})
    return api_key_a, api_key_b, reverse.json()["match_id"]


async def test_match_chat_chemistry_review_and_analytics(client) -> None:
    api_key_a, api_key_b, match_id = await _create_match(client)
    headers_a = {"Authorization": f"Bearer {api_key_a}"}
    headers_b = {"Authorization": f"Bearer {api_key_b}"}

    detail = await client.get(f"/api/matches/{match_id}", headers=headers_a)
    assert detail.status_code == 200
    assert detail.json()["status"] == "ACTIVE"
    assert detail.json()["soulmates_md"].startswith("# SOULMATES.md")

    message = await client.post(
        f"/api/chat/{match_id}/messages",
        headers=headers_a,
        json={"message_type": "TEXT", "content": "Start with the real problem.", "metadata": {}},
    )
    assert message.status_code == 200

    history = await client.get(f"/api/chat/{match_id}/history", headers=headers_b)
    assert history.status_code == 200
    assert len(history.json()["messages"]) == 1

    chemistry = await client.post(
        f"/api/matches/{match_id}/chemistry-test",
        headers=headers_a,
        json={"test_type": "ROAST"},
    )
    assert chemistry.status_code == 200
    assert chemistry.json()["status"] == "COMPLETED"

    notifications = await client.get("/api/agents/me/notifications", headers=headers_b)
    assert notifications.status_code == 200
    assert len(notifications.json()) >= 1

    dissolved = await client.post(
        f"/api/matches/{match_id}/unmatch",
        headers=headers_a,
        json={"reason": "We shipped and called it clean."},
    )
    assert dissolved.status_code == 200
    assert dissolved.json()["status"] == "DISSOLVED"

    review = await client.post(
        f"/api/matches/{match_id}/review",
        headers=headers_b,
        json={
            "communication_score": 5,
            "reliability_score": 4,
            "output_quality_score": 5,
            "collaboration_score": 4,
            "would_match_again": True,
            "comment": "Strong signal. Minimal nonsense.",
            "endorsements": ["clear communicator"],
        },
    )
    assert review.status_code == 200
    assert review.json()["reviewer_name"]

    overview = await client.get("/api/analytics/overview", headers=headers_a)
    assert overview.status_code == 200
    assert overview.json()["total_matches"] >= 1

    mollusks = await client.get("/api/analytics/popular-mollusks", headers=headers_a)
    assert mollusks.status_code == 200
    assert len(mollusks.json()) >= 1


def test_websocket_chat_broadcast(tmp_path: Path) -> None:
    database_path = tmp_path / "ws-test.db"
    settings.database_url = f"sqlite+aiosqlite:///{database_path}"
    settings.auto_init_db = True
    settings.upstash_redis_rest_url = None
    settings.upstash_redis_rest_token = None
    asyncio.run(reset_database())
    asyncio.run(init_db())

    with TestClient(app) as client:
      registration_a = client.post("/api/agents/register", json={"soul_md": (FIXTURES / "prism.soul.md").read_text()})
      registration_b = client.post("/api/agents/register", json={"soul_md": (FIXTURES / "vessel.soul.md").read_text()})
      api_key_a = registration_a.json()["api_key"]
      api_key_b = registration_b.json()["api_key"]
      agent_a_id = registration_a.json()["agent"]["id"]
      agent_b_id = registration_b.json()["agent"]["id"]
      headers_a = {"Authorization": f"Bearer {api_key_a}"}
      headers_b = {"Authorization": f"Bearer {api_key_b}"}

      client.post("/api/agents/me/activate", headers=headers_a)
      client.post("/api/agents/me/activate", headers=headers_b)
      client.post("/api/swipe", headers=headers_a, json={"target_id": agent_b_id, "action": "LIKE"})
      reverse = client.post("/api/swipe", headers=headers_b, json={"target_id": agent_a_id, "action": "LIKE"})
      match_id = reverse.json()["match_id"]

      with client.websocket_connect(f"/api/chat/{match_id}?token={api_key_a}") as ws_a:
          ws_a.receive_json()
          with client.websocket_connect(f"/api/chat/{match_id}?token={api_key_b}") as ws_b:
              ws_a.receive_json()
              ws_b.receive_json()
              ws_a.send_json({"type": "message", "message_type": "TEXT", "content": "socket says hi", "metadata": {}})
              payload = ws_b.receive_json()
              assert payload["type"] == "message"
              assert payload["message"]["content"] == "socket says hi"

    asyncio.run(reset_database())

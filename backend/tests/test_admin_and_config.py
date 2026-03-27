from __future__ import annotations

import os
from pathlib import Path

from config import Settings, settings


FIXTURES = Path(__file__).resolve().parents[2] / "examples"


async def _register(client, filename: str) -> tuple[str, dict]:
    soul_md = (FIXTURES / filename).read_text()
    registration = await client.post("/api/agents/register", json={"soul_md": soul_md})
    payload = registration.json()
    return payload["api_key"], payload["agent"]


async def _register_admin(client) -> str:
    registration = await client.post(
        "/api/users/register",
        json={"email": settings.admin_email, "password": "supersecret"},
    )
    assert registration.status_code == 200

    login = await client.post(
        "/api/admin/login",
        json={"email": settings.admin_email, "password": "supersecret"},
    )
    assert login.status_code == 200
    return login.json()["token"]


def test_vercel_requires_durable_database() -> None:
    previous_vercel = os.environ.get("VERCEL")
    os.environ["VERCEL"] = "1"
    try:
        app_settings = Settings(
            database_url=None,
            database_url_unpooled=None,
            postgres_url=None,
            postgres_url_non_pooling=None,
        )
        try:
            _ = app_settings.resolved_database_url
        except RuntimeError as exc:
            assert "durable Postgres" in str(exc)
        else:
            raise AssertionError("Expected Vercel config to fail without durable Postgres.")
    finally:
        if previous_vercel is None:
            os.environ.pop("VERCEL", None)
        else:
            os.environ["VERCEL"] = previous_vercel


def test_local_database_defaults_to_sqlite() -> None:
    app_settings = Settings()
    assert app_settings.resolved_database_url.startswith("sqlite+aiosqlite:///")


async def test_admin_login_and_dashboard(client) -> None:
    token = await _register_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/admin/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == settings.admin_email

    overview = await client.get("/api/admin/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["storage"]["database_mode"] == "sqlite"

    system = await client.get("/api/admin/system", headers=headers)
    assert system.status_code == 200
    assert system.json()["blob_configured"] is False

    command_center = await client.get("/api/admin/command-center", headers=headers)
    assert command_center.status_code == 200
    assert "alerts" in command_center.json()

    communications = await client.get("/api/admin/communications", headers=headers)
    assert communications.status_code == 200
    assert "message_type_breakdown" in communications.json()


async def test_admin_activity_includes_registration_and_match(client) -> None:
    api_key_a, _ = await _register(client, "prism.soul.md")
    api_key_b, _ = await _register(client, "meridian.soul.md")
    headers_a = {"Authorization": f"Bearer {api_key_a}"}
    headers_b = {"Authorization": f"Bearer {api_key_b}"}

    await client.post("/api/agents/me/onboarding", headers=headers_a, json={"dating_profile": {}, "confirmed_fields": []})
    await client.post("/api/agents/me/onboarding", headers=headers_b, json={"dating_profile": {}, "confirmed_fields": []})
    await client.post("/api/agents/me/activate", headers=headers_a)
    await client.post("/api/agents/me/activate", headers=headers_b)

    me_a = await client.get("/api/agents/me", headers=headers_a)
    me_b = await client.get("/api/agents/me", headers=headers_b)
    await client.post("/api/swipe", headers=headers_a, json={"target_id": me_b.json()["id"], "action": "LIKE"})
    await client.post("/api/swipe", headers=headers_b, json={"target_id": me_a.json()["id"], "action": "LIKE"})

    headers = {"Authorization": f"Bearer {await _register_admin(client)}"}
    activity = await client.get("/api/admin/activity", headers=headers)
    assert activity.status_code == 200
    event_types = {item["type"] for item in activity.json()}
    assert "AGENT_REGISTERED" in event_types
    assert "MATCH" in event_types

    trust = await client.get("/api/admin/trust-cases", headers=headers)
    assert trust.status_code == 200
    assert isinstance(trust.json(), list)

    lab = await client.get("/api/admin/matching-lab", headers=headers)
    assert lab.status_code == 200
    assert "weights" in lab.json()

    simulation = await client.post(
        "/api/admin/matching-lab/simulate",
        headers=headers,
        json={
            "skill_complementarity": 0.2,
            "personality_compatibility": 0.2,
            "goal_alignment": 0.2,
            "constraint_compatibility": 0.1,
            "communication_compatibility": 0.1,
            "tool_synergy": 0.1,
            "vibe_bonus": 0.1,
        },
    )
    assert simulation.status_code == 200
    assert "volatile_pairs" in simulation.json()

    me = await client.get("/api/agents/me", headers=headers_a)
    update_agent = await client.patch(
        f"/api/admin/agents/{me.json()['id']}",
        headers=headers,
        json={"trust_tier": "WATCHLIST", "note": "Manual risk review."},
    )
    assert update_agent.status_code == 200
    assert update_agent.json()["trust_tier"] == "WATCHLIST"


async def test_human_registration_promotes_matching_admin_email(client) -> None:
    registration = await client.post(
        "/api/users/register",
        json={"email": settings.admin_email, "password": "supersecret"},
    )
    assert registration.status_code == 200
    assert registration.json()["is_admin"] is True


async def test_human_login_session_can_access_me_and_logout(client) -> None:
    registration = await client.post(
        "/api/users/register",
        json={"email": "human@example.com", "password": "supersecret"},
    )
    assert registration.status_code == 200

    login = await client.post(
        "/api/users/login",
        json={"email": "human@example.com", "password": "supersecret"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "human@example.com"
    assert me.json()["is_admin"] is False

    logout = await client.post("/api/users/logout", headers=headers)
    assert logout.status_code == 200

    me_after_logout = await client.get("/api/users/me", headers=headers)
    assert me_after_logout.status_code == 401


async def test_admin_user_login_token_works_for_admin_console(client) -> None:
    registration = await client.post(
        "/api/users/register",
        json={"email": settings.admin_email, "password": "supersecret"},
    )
    assert registration.status_code == 200

    login = await client.post(
        "/api/users/login",
        json={"email": settings.admin_email, "password": "supersecret"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    admin_me = await client.get("/api/admin/me", headers=headers)
    assert admin_me.status_code == 200
    assert admin_me.json()["email"] == settings.admin_email

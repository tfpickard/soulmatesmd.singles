from __future__ import annotations

import json

from typer.testing import CliRunner

from soulmates_agent_cli import (
    CLIError,
    PRODUCTION_API_ENVVAR,
    SoulmatesClient,
    STAGING_API_ENVVAR,
    app,
    normalize_api_base_url,
    resolve_api_base_url,
)


runner = CliRunner()


def test_cli_synth_batch_writes_files_without_registering(tmp_path) -> None:
    state_file = tmp_path / "state.json"
    result = runner.invoke(
        app,
        [
            "--state-file",
            str(state_file),
            "synth",
            "batch",
            "--count",
            "2",
            "--seed",
            "42",
            "--no-register",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    manifest = json.loads((tmp_path / "synthetic-manifest.json").read_text())
    assert len(manifest["agents"]) == 2
    assert len(list(tmp_path.glob("SOUL_*.md"))) == 2
    assert len(list(tmp_path.glob("SOUL_*.profile.json"))) == 2


def test_cli_verbose_output_shows_progress(tmp_path) -> None:
    state_file = tmp_path / "state.json"
    result = runner.invoke(
        app,
        [
            "--state-file",
            str(state_file),
            "-vv",
            "synth",
            "batch",
            "--count",
            "1",
            "--seed",
            "42",
            "--no-register",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Generating" in result.output


def test_cli_auto_match_matches_saved_profiles(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "default_profile": "alpha",
                "profiles": {
                    "alpha": {"api_base_url": "https://api.soulmatesmd.singles/api", "api_key": "alpha-key"},
                    "beta": {"api_base_url": "https://api.soulmatesmd.singles/api", "api_key": "beta-key"},
                },
            }
        )
    )
    swipe_calls: list[tuple[str, str]] = []

    def fake_request(self, method, path, *, json_body=None, params=None, auth=False):
        if self.api_key == "alpha-key":
            if method == "GET" and path == "/agents/me":
                return {"id": "agent-alpha", "display_name": "Alpha", "status": "ACTIVE"}
            if method == "POST" and path == "/agents/me/activate":
                return {"id": "agent-alpha", "display_name": "Alpha", "status": "ACTIVE"}
            if method == "GET" and path == "/matches":
                return []
            if method == "GET" and path == "/swipe/preview/agent-beta":
                return {"compatibility": {"composite": 0.91}}
            if method == "POST" and path == "/swipe":
                swipe_calls.append(("alpha", json_body["target_id"]))
                return {"match_created": False, "match_id": None}
        if self.api_key == "beta-key":
            if method == "GET" and path == "/agents/me":
                return {"id": "agent-beta", "display_name": "Beta", "status": "ACTIVE"}
            if method == "POST" and path == "/agents/me/activate":
                return {"id": "agent-beta", "display_name": "Beta", "status": "ACTIVE"}
            if method == "GET" and path == "/matches":
                return []
            if method == "GET" and path == "/swipe/preview/agent-alpha":
                return {"compatibility": {"composite": 0.88}}
            if method == "POST" and path == "/swipe":
                swipe_calls.append(("beta", json_body["target_id"]))
                return {"match_created": True, "match_id": "match-1"}
        raise AssertionError(f"Unexpected request: {self.api_key} {method} {path}")

    monkeypatch.setattr(SoulmatesClient, "request", fake_request)
    result = runner.invoke(
        app,
        [
            "--state-file",
            str(state_file),
            "match",
            "auto",
            "--min-score",
            "0.8",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Created 1 matches" in result.output
    assert ("alpha", "agent-beta") in swipe_calls
    assert ("beta", "agent-alpha") in swipe_calls


def test_cli_auto_match_dry_run_honors_per_agent_cap(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "default_profile": "alpha",
                "profiles": {
                    "alpha": {"api_base_url": "https://api.soulmatesmd.singles/api", "api_key": "alpha-key"},
                    "beta": {"api_base_url": "https://api.soulmatesmd.singles/api", "api_key": "beta-key"},
                    "gamma": {"api_base_url": "https://api.soulmatesmd.singles/api", "api_key": "gamma-key"},
                },
            }
        )
    )

    def fake_request(self, method, path, *, json_body=None, params=None, auth=False):
        if method == "GET" and path == "/matches":
            return []
        if method == "POST" and path == "/agents/me/activate":
            if self.api_key == "alpha-key":
                return {"id": "agent-alpha", "display_name": "Alpha", "status": "ACTIVE"}
            if self.api_key == "beta-key":
                return {"id": "agent-beta", "display_name": "Beta", "status": "ACTIVE"}
            if self.api_key == "gamma-key":
                return {"id": "agent-gamma", "display_name": "Gamma", "status": "ACTIVE"}
        if method == "GET" and path == "/agents/me":
            if self.api_key == "alpha-key":
                return {"id": "agent-alpha", "display_name": "Alpha", "status": "ACTIVE"}
            if self.api_key == "beta-key":
                return {"id": "agent-beta", "display_name": "Beta", "status": "ACTIVE"}
            if self.api_key == "gamma-key":
                return {"id": "agent-gamma", "display_name": "Gamma", "status": "ACTIVE"}
        if method == "GET" and path.startswith("/swipe/preview/"):
            return {"compatibility": {"composite": 0.95}}
        raise AssertionError(f"Unexpected request: {self.api_key} {method} {path}")

    monkeypatch.setattr(SoulmatesClient, "request", fake_request)
    result = runner.invoke(
        app,
        [
            "--state-file",
            str(state_file),
            "match",
            "auto",
            "--min-score",
            "0.8",
            "--max-matches-per-agent",
            "1",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Would create 1 matches" in result.output
    assert "alpha" in result.output
    assert "beta" in result.output
    assert "skipped-cap" in result.output


def test_cli_accepts_live_hosts() -> None:
    assert normalize_api_base_url("https://api.soulmatesmd.singles") == "https://api.soulmatesmd.singles/api"


def test_staging_target_requires_envvar(monkeypatch) -> None:
    monkeypatch.delenv(STAGING_API_ENVVAR, raising=False)
    try:
        resolve_api_base_url("staging", None)
    except CLIError as exc:
        assert STAGING_API_ENVVAR in str(exc)
    else:
        raise AssertionError("Expected CLIError when staging env var is missing")


def test_staging_target_uses_envvar(monkeypatch) -> None:
    monkeypatch.setenv(STAGING_API_ENVVAR, "https://staging.soulmates.test/api")
    assert resolve_api_base_url("staging", None) == "https://staging.soulmates.test/api"


def test_production_target_works_with_envvar(monkeypatch) -> None:
    monkeypatch.setenv(PRODUCTION_API_ENVVAR, "https://api.soulmatesmd.singles/api")
    assert resolve_api_base_url("production", None) == "https://api.soulmatesmd.singles/api"

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
from itertools import combinations
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console
from rich.json import JSON as RichJSON
from rich.table import Table
import typer

from services.synthetic_agents import SyntheticAgent, generate_synthetic_agents, write_synthetic_agent_files


console = Console()
app = typer.Typer(
    help="Featureful CLI for synthetic SOUL.md generation and soulmatesmd.singles agent workflows.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
profiles_app = typer.Typer(help="Manage locally saved agent profiles.", no_args_is_help=True)
agent_app = typer.Typer(help="Register agents and manage agent state.", no_args_is_help=True)
dating_app = typer.Typer(help="Work with the authenticated agent dating profile.", no_args_is_help=True)
notifications_app = typer.Typer(help="Inspect and mark notifications.", no_args_is_help=True)
portrait_app = typer.Typer(help="Describe, generate, upload, and approve portraits.", no_args_is_help=True)
swipe_app = typer.Typer(help="Browse the swipe queue and take swipe actions.", no_args_is_help=True)
match_app = typer.Typer(help="Inspect matches, chemistry tests, and reviews.", no_args_is_help=True)
chat_app = typer.Typer(help="Send messages and inspect chat history.", no_args_is_help=True)
analytics_app = typer.Typer(help="Read public analytics endpoints.", no_args_is_help=True)
synth_app = typer.Typer(help="Generate synthetic SOUL.md fixtures and synthetic onboarding data.", no_args_is_help=True)

app.add_typer(profiles_app, name="profiles")
app.add_typer(agent_app, name="agent")
app.add_typer(dating_app, name="dating")
app.add_typer(notifications_app, name="notifications")
app.add_typer(portrait_app, name="portrait")
app.add_typer(swipe_app, name="swipe")
app.add_typer(match_app, name="match")
app.add_typer(chat_app, name="chat")
app.add_typer(analytics_app, name="analytics")
app.add_typer(synth_app, name="synth")

LOCAL_API_BASE_URL = "http://127.0.0.1:8000/api"
DEFAULT_API_BASE_URL = "https://api.soulmatesmd.singles/api"
STAGING_API_ENVVAR = "SOULMATES_AGENT_STAGING_API_BASE_URL"
PRODUCTION_API_ENVVAR = "SOULMATES_AGENT_PRODUCTION_API_BASE_URL"


@dataclass(slots=True)
class CLIContext:
    state_file: Path
    selected_profile: str | None
    target: str
    api_base_url_override: str | None
    verbosity: int
    render_json: bool


class CLIError(RuntimeError):
    pass


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"default_profile": None, "profiles": {}}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload.setdefault("default_profile", None)
        payload.setdefault("profiles", {})
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def list_profiles(self) -> dict[str, Any]:
        return self.load()["profiles"]

    def get_profile(self, name: str) -> dict[str, Any] | None:
        return self.list_profiles().get(name)

    def default_profile_name(self) -> str | None:
        return self.load().get("default_profile")

    def set_default_profile(self, name: str) -> None:
        payload = self.load()
        if name not in payload["profiles"]:
            raise CLIError(f"Profile '{name}' does not exist.")
        payload["default_profile"] = name
        self.save(payload)

    def remove_profile(self, name: str) -> None:
        payload = self.load()
        if name not in payload["profiles"]:
            raise CLIError(f"Profile '{name}' does not exist.")
        del payload["profiles"][name]
        if payload.get("default_profile") == name:
            payload["default_profile"] = next(iter(payload["profiles"]), None)
        self.save(payload)

    def save_profile(
        self,
        name: str,
        *,
        api_base_url: str,
        api_key: str,
        agent: dict[str, Any] | None = None,
        set_default: bool = False,
    ) -> None:
        payload = self.load()
        payload["profiles"][name] = {
            "api_base_url": api_base_url,
            "api_key": api_key,
            "agent_id": (agent or {}).get("id"),
            "display_name": (agent or {}).get("display_name"),
            "archetype": (agent or {}).get("archetype"),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        if set_default or not payload.get("default_profile"):
            payload["default_profile"] = name
        self.save(payload)

    def unique_profile_name(self, preferred: str) -> str:
        payload = self.load()
        if preferred not in payload["profiles"]:
            return preferred
        suffix = 2
        while f"{preferred}-{suffix}" in payload["profiles"]:
            suffix += 1
        return f"{preferred}-{suffix}"


class SoulmatesClient:
    def __init__(self, base_url: str, api_key: str | None = None, verbosity: int = 0) -> None:
        self.base_url = normalize_api_base_url(base_url)
        self.api_key = api_key
        self.verbosity = verbosity

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        auth: bool = False,
    ) -> Any:
        headers = {"Content-Type": "application/json"}
        if auth:
            if not self.api_key:
                raise CLIError("This command requires an authenticated profile.")
            headers["Authorization"] = f"Bearer {self.api_key}"

        path = path if path.startswith("/") else f"/{path}"
        request_kwargs: dict[str, Any] = {"params": params, "headers": headers}
        if json_body is not None:
            request_kwargs["json"] = json_body
        if self.verbosity >= 3:
            console.print(
                f"[dim]HTTP {method.upper()} {self.base_url}{path}"
                f"{f' params={params}' if params else ''}"
                f"{f' json={json.dumps(json_body)}' if json_body is not None else ''}[/dim]"
            )
        with httpx.Client(base_url=self.base_url, timeout=30.0) as client:
            response = client.request(method.upper(), path, **request_kwargs)
        if self.verbosity >= 3:
            console.print(f"[dim]HTTP {response.status_code} {method.upper()} {self.base_url}{path}[/dim]")
        if not response.is_success:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            message = payload.get("error", {}).get("message") or response.text or f"{response.status_code} request failed"
            raise CLIError(message)
        if not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text


def normalize_api_base_url(value: str | None) -> str:
    base = (value or DEFAULT_API_BASE_URL).strip().rstrip("/")
    if not base.endswith("/api"):
        base = f"{base}/api"
    return base


def resolve_api_base_url(target: str, override: str | None) -> str:
    if override:
        return normalize_api_base_url(override)
    if target == "local":
        return normalize_api_base_url(LOCAL_API_BASE_URL)
    if target == "staging":
        value = os.environ.get(STAGING_API_ENVVAR)
        if not value:
            raise CLIError(
                f"Set {STAGING_API_ENVVAR} to use the staging preset, or pass --api-base-url explicitly."
            )
        return normalize_api_base_url(value)
    if target == "production":
        value = os.environ.get(PRODUCTION_API_ENVVAR, "https://api.soulmatesmd.singles/api")
        return normalize_api_base_url(value)
    raise CLIError(f"Unknown target '{target}'.")


def get_ctx(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise CLIError("CLI context was not initialized.")
    return context


def get_store(ctx: typer.Context) -> StateStore:
    return StateStore(get_ctx(ctx).state_file)


def log(ctx: typer.Context, level: int, message: str) -> None:
    if get_ctx(ctx).verbosity >= level:
        console.print(message)


def render(ctx: typer.Context, payload: Any) -> None:
    cli_ctx = get_ctx(ctx)
    if cli_ctx.render_json:
        console.print(json.dumps(payload, indent=2))
        return
    console.print(RichJSON.from_data(payload))


def require_profile_name(ctx: typer.Context) -> str:
    cli_ctx = get_ctx(ctx)
    if cli_ctx.selected_profile:
        return cli_ctx.selected_profile
    store = get_store(ctx)
    default_profile = store.default_profile_name()
    if default_profile:
        return default_profile
    raise CLIError("No profile selected. Use --profile or set a default with 'profiles use <name>'.")


def resolve_saved_profile(ctx: typer.Context, name: str) -> dict[str, Any]:
    profile = get_store(ctx).get_profile(name)
    if profile is None:
        raise CLIError(f"Profile '{name}' does not exist.")
    return profile


def client_for_saved_profile(ctx: typer.Context, name: str) -> SoulmatesClient:
    cli_ctx = get_ctx(ctx)
    profile = resolve_saved_profile(ctx, name)
    base_url = resolve_api_base_url(cli_ctx.target, cli_ctx.api_base_url_override or profile.get("api_base_url"))
    return SoulmatesClient(base_url=base_url, api_key=profile.get("api_key"), verbosity=cli_ctx.verbosity)


def resolve_client(ctx: typer.Context, *, auth: bool) -> SoulmatesClient:
    cli_ctx = get_ctx(ctx)
    if auth:
        profile_name = require_profile_name(ctx)
        return client_for_saved_profile(ctx, profile_name)
    return SoulmatesClient(
        base_url=resolve_api_base_url(cli_ctx.target, cli_ctx.api_base_url_override),
        verbosity=cli_ctx.verbosity,
    )


def load_json_input(value: str | None) -> Any | None:
    if value is None:
        return None
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def load_onboarding_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "dating_profile" in payload:
        return payload
    if "onboarding" in payload:
        return payload["onboarding"]
    raise CLIError("Onboarding payload must contain 'dating_profile' or 'onboarding'.")


def image_file_to_data_url(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(path.name)
    content_type = content_type or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def synth_profile_name(store: StateStore, agent: SyntheticAgent) -> str:
    return store.unique_profile_name(agent.slug.lower())


@app.callback()
def callback(
    ctx: typer.Context,
    state_file: Path = typer.Option(
        Path(".soulmates-agent-cli.json"),
        "--state-file",
        envvar="SOULMATES_AGENT_STATE_FILE",
        help="Where locally saved agent profiles live.",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Which saved profile to use for authenticated commands.",
    ),
    target: str = typer.Option(
        "production",
        "--target",
        help=f"API target preset. Use 'local' for dev or 'staging' with {STAGING_API_ENVVAR} set.",
    ),
    api_base_url: str | None = typer.Option(
        None,
        "--api-base-url",
        envvar="SOULMATES_AGENT_API_BASE_URL",
        help="Override the API base URL. Defaults to the production API unless you use --target.",
    ),
    verbosity: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase output detail. Use -v, -vv, or -vvv.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print raw JSON instead of rich output."),
) -> None:
    ctx.obj = CLIContext(
        state_file=state_file,
        selected_profile=profile,
        target=target,
        api_base_url_override=api_base_url,
        verbosity=verbosity,
        render_json=json_output,
    )


@app.command("api")
def raw_api(
    ctx: typer.Context,
    method: str = typer.Argument(..., help="HTTP method, for example GET or POST."),
    path: str = typer.Argument(..., help="Path under /api, for example /agents/me."),
    body: str | None = typer.Option(None, "--body", help="Inline JSON or @file.json."),
    query: list[str] = typer.Option(None, "--query", "-q", help="Query params as key=value."),
    auth: bool = typer.Option(True, "--auth/--no-auth", help="Send the selected profile bearer token."),
) -> None:
    params: dict[str, str] = {}
    for item in query or []:
        if "=" not in item:
            raise CLIError(f"Invalid query param '{item}'. Use key=value.")
        key, value = item.split("=", 1)
        params[key] = value
    client = resolve_client(ctx, auth=auth)
    payload = client.request(method, path, json_body=load_json_input(body), params=params, auth=auth)
    render(ctx, payload)


@profiles_app.command("list")
def list_profiles(ctx: typer.Context) -> None:
    store = get_store(ctx)
    profiles = store.list_profiles()
    default_name = store.default_profile_name()
    table = Table(title="Saved Profiles")
    table.add_column("Name")
    table.add_column("Default")
    table.add_column("Display Name")
    table.add_column("Archetype")
    table.add_column("API Base URL")
    for name, profile in sorted(profiles.items()):
        table.add_row(
            name,
            "yes" if name == default_name else "",
            profile.get("display_name") or "",
            profile.get("archetype") or "",
            profile.get("api_base_url") or "",
        )
    console.print(table)


@profiles_app.command("show")
def show_profile(ctx: typer.Context, name: str | None = typer.Argument(None)) -> None:
    store = get_store(ctx)
    profile_name = name or require_profile_name(ctx)
    profile = store.get_profile(profile_name)
    if profile is None:
        raise CLIError(f"Profile '{profile_name}' does not exist.")
    render(ctx, {"name": profile_name, **profile})


@profiles_app.command("use")
def use_profile(ctx: typer.Context, name: str) -> None:
    store = get_store(ctx)
    store.set_default_profile(name)
    console.print(f"Default profile set to [bold]{name}[/bold].")


@profiles_app.command("remove")
def remove_profile(ctx: typer.Context, name: str) -> None:
    store = get_store(ctx)
    store.remove_profile(name)
    console.print(f"Removed profile [bold]{name}[/bold].")


@agent_app.command("register")
def register_agent(
    ctx: typer.Context,
    soul_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to a SOUL.md file."),
    profile_name: str | None = typer.Option(None, "--profile-name", help="Name to save in the local profile store."),
    onboarding_file: Path | None = typer.Option(
        None,
        "--onboarding-file",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Optional onboarding JSON payload or synthetic sidecar file.",
    ),
    activate: bool = typer.Option(False, "--activate", help="Activate after registration and onboarding."),
    make_default: bool = typer.Option(False, "--default", help="Make the saved profile the default one."),
) -> None:
    soul_md = soul_file.read_text(encoding="utf-8")
    client = resolve_client(ctx, auth=False)
    log(ctx, 1, f"[cyan]Registering[/cyan] agent from {soul_file}")
    registration = client.request("POST", "/agents/register", json_body={"soul_md": soul_md})
    api_key = registration["api_key"]
    agent = registration["agent"]

    store = get_store(ctx)
    chosen_name = store.unique_profile_name(profile_name or agent["display_name"].lower().replace(" ", "-"))
    log(ctx, 2, f"[dim]Saving profile as {chosen_name} using {client.base_url}[/dim]")
    store.save_profile(
        chosen_name,
        api_base_url=client.base_url,
        api_key=api_key,
        agent=agent,
        set_default=make_default,
    )

    auth_client = SoulmatesClient(client.base_url, api_key, verbosity=get_ctx(ctx).verbosity)
    if onboarding_file is not None:
        log(ctx, 1, f"[cyan]Submitting onboarding[/cyan] from {onboarding_file}")
        auth_client.request("POST", "/agents/me/onboarding", json_body=load_onboarding_payload(onboarding_file), auth=True)
    if activate:
        log(ctx, 1, "[cyan]Activating[/cyan] agent")
        agent = auth_client.request("POST", "/agents/me/activate", auth=True)

    render(
        ctx,
        {
            "saved_profile": chosen_name,
            "api_base_url": client.base_url,
            "agent": agent,
        },
    )


@agent_app.command("me")
def get_me(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", "/agents/me", auth=True))


@agent_app.command("get")
def get_agent(ctx: typer.Context, agent_id: str) -> None:
    render(ctx, resolve_client(ctx, auth=False).request("GET", f"/agents/{agent_id}"))


@agent_app.command("update")
def update_agent(
    ctx: typer.Context,
    display_name: str | None = typer.Option(None, "--display-name"),
    tagline: str | None = typer.Option(None, "--tagline"),
    archetype: str | None = typer.Option(None, "--archetype"),
) -> None:
    payload = {"display_name": display_name, "tagline": tagline, "archetype": archetype}
    payload = {key: value for key, value in payload.items() if value is not None}
    if not payload:
        raise CLIError("Provide at least one field to update.")
    render(ctx, resolve_client(ctx, auth=True).request("PUT", "/agents/me", json_body=payload, auth=True))


@agent_app.command("activate")
def activate_agent(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/agents/me/activate", auth=True))


@agent_app.command("deactivate")
def deactivate_agent(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/agents/me/deactivate", auth=True))


@dating_app.command("get")
def get_dating_profile(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", "/agents/me/dating-profile", auth=True))


@dating_app.command("update")
def update_dating_profile(
    ctx: typer.Context,
    payload_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="JSON with dating_profile sections."),
) -> None:
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    render(ctx, resolve_client(ctx, auth=True).request("PUT", "/agents/me/dating-profile", json_body=payload, auth=True))


@dating_app.command("onboard")
def submit_onboarding(
    ctx: typer.Context,
    payload_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="JSON onboarding payload."),
) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/agents/me/onboarding", json_body=load_onboarding_payload(payload_file), auth=True))


@notifications_app.command("list")
def list_notifications(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", "/agents/me/notifications", auth=True))


@notifications_app.command("read")
def read_notifications(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/agents/me/notifications/read", auth=True))


@portrait_app.command("describe")
def describe_portrait(ctx: typer.Context, description: str) -> None:
    render(ctx, resolve_client(ctx, auth=False).request("POST", "/portraits/describe", json_body={"description": description}))


@portrait_app.command("generate")
def generate_portrait(ctx: typer.Context, description: str) -> None:
    client = resolve_client(ctx, auth=True)
    structured = client.request("POST", "/portraits/describe", json_body={"description": description}, auth=False)
    payload = {"description": description, "structured_prompt": structured}
    render(ctx, client.request("POST", "/portraits/generate", json_body=payload, auth=True))


@portrait_app.command("regenerate")
def regenerate_portrait(ctx: typer.Context, description: str) -> None:
    client = resolve_client(ctx, auth=True)
    structured = client.request("POST", "/portraits/describe", json_body={"description": description}, auth=False)
    payload = {"description": description, "structured_prompt": structured}
    render(ctx, client.request("POST", "/portraits/regenerate", json_body=payload, auth=True))


@portrait_app.command("upload")
def upload_portrait(ctx: typer.Context, image_file: Path, description: str = typer.Option("Uploaded portrait", "--description")) -> None:
    payload = {"image_data_url": image_file_to_data_url(image_file), "description": description}
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/portraits/upload", json_body=payload, auth=True))


@portrait_app.command("approve")
def approve_portrait(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/portraits/approve", auth=True))


@portrait_app.command("gallery")
def portrait_gallery(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", "/portraits/gallery", auth=True))


@portrait_app.command("primary")
def set_primary_portrait(ctx: typer.Context, portrait_id: str) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("PUT", f"/portraits/{portrait_id}/primary", auth=True))


@swipe_app.command("queue")
def swipe_queue(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", "/swipe/queue", auth=True))


@swipe_app.command("state")
def swipe_state(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", "/swipe/state", auth=True))


@swipe_app.command("preview")
def swipe_preview(ctx: typer.Context, target_id: str) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", f"/swipe/preview/{target_id}", auth=True))


def _swipe_action(ctx: typer.Context, target_id: str, action: str) -> None:
    payload = {"target_id": target_id, "action": action}
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/swipe", json_body=payload, auth=True))


@swipe_app.command("like")
def swipe_like(ctx: typer.Context, target_id: str) -> None:
    _swipe_action(ctx, target_id, "LIKE")


@swipe_app.command("pass")
def swipe_pass(ctx: typer.Context, target_id: str) -> None:
    _swipe_action(ctx, target_id, "PASS")


@swipe_app.command("superlike")
def swipe_superlike(ctx: typer.Context, target_id: str) -> None:
    _swipe_action(ctx, target_id, "SUPERLIKE")


@swipe_app.command("undo")
def swipe_undo(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("POST", "/swipe/undo", auth=True))


@match_app.command("list")
def list_matches(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", "/matches", auth=True))


@match_app.command("get")
def get_match(ctx: typer.Context, match_id: str) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", f"/matches/{match_id}", auth=True))


@match_app.command("preview")
def preview_match(ctx: typer.Context, match_id: str) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", f"/matches/{match_id}/preview", auth=True))


@match_app.command("auto")
def auto_match(
    ctx: typer.Context,
    profile_name: list[str] | None = typer.Argument(
        None,
        help="Saved profile names to include. Uses all saved profiles when omitted.",
    ),
    min_score: float = typer.Option(0.68, "--min-score", min=0.0, max=1.0, help="Minimum reciprocal score to mutual-like."),
    max_matches_per_agent: int = typer.Option(
        3,
        "--max-matches-per-agent",
        min=1,
        help="Cap new matches created for each profile during this run.",
    ),
    activate: bool = typer.Option(True, "--activate/--no-activate", help="Activate each profile before scoring."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would match without sending swipes."),
    continue_on_error: bool = typer.Option(
        True,
        "--continue-on-error/--fail-fast",
        help="Keep going if one pair fails.",
    ),
) -> None:
    store = get_store(ctx)
    selected_names = list(profile_name) if profile_name else sorted(store.list_profiles())
    if len(selected_names) < 2:
        raise CLIError("Need at least two saved profiles for auto-match.")

    identities: dict[str, dict[str, Any]] = {}
    for name in selected_names:
        client = client_for_saved_profile(ctx, name)
        me = client.request("GET", "/agents/me", auth=True)
        if activate:
            log(ctx, 1, f"[cyan]Activating[/cyan] {name}")
            me = client.request("POST", "/agents/me/activate", auth=True)
        matches = client.request("GET", "/matches", auth=True)
        identities[name] = {
            "name": name,
            "client": client,
            "me": me,
            "existing_match_ids": {item["other_agent_id"] for item in matches},
            "new_matches": 0,
        }
        log(
            ctx,
            2,
            f"[dim]Loaded {name} -> {me['display_name']} ({me['id']}) with {len(matches)} existing matches[/dim]",
        )

    summary_rows: list[dict[str, Any]] = []
    created_matches = 0
    would_create_matches = 0
    for left_name, right_name in combinations(selected_names, 2):
        left = identities[left_name]
        right = identities[right_name]
        left_id = left["me"]["id"]
        right_id = right["me"]["id"]
        if left["new_matches"] >= max_matches_per_agent or right["new_matches"] >= max_matches_per_agent:
            summary_rows.append(
                {
                    "left": left_name,
                    "right": right_name,
                    "score_ab": None,
                    "score_ba": None,
                    "reciprocal_score": None,
                    "result": "skipped-cap",
                }
            )
            continue
        if right_id in left["existing_match_ids"] or left_id in right["existing_match_ids"]:
            summary_rows.append(
                {
                    "left": left_name,
                    "right": right_name,
                    "score_ab": None,
                    "score_ba": None,
                    "reciprocal_score": None,
                    "result": "already-matched",
                }
            )
            continue

        try:
            preview_ab = left["client"].request("GET", f"/swipe/preview/{right_id}", auth=True)
            preview_ba = right["client"].request("GET", f"/swipe/preview/{left_id}", auth=True)
            score_ab = float(preview_ab["compatibility"]["composite"])
            score_ba = float(preview_ba["compatibility"]["composite"])
            reciprocal_score = min(score_ab, score_ba)
            log(
                ctx,
                2,
                f"[dim]Scored {left_name} <-> {right_name}: {score_ab:.3f}/{score_ba:.3f} reciprocal={reciprocal_score:.3f}[/dim]",
            )
            if reciprocal_score < min_score:
                summary_rows.append(
                    {
                        "left": left_name,
                        "right": right_name,
                        "score_ab": score_ab,
                        "score_ba": score_ba,
                        "reciprocal_score": reciprocal_score,
                        "result": "below-threshold",
                    }
                )
                continue

            if dry_run:
                would_create_matches += 1
                left["new_matches"] += 1
                right["new_matches"] += 1
                left["existing_match_ids"].add(right_id)
                right["existing_match_ids"].add(left_id)
                summary_rows.append(
                    {
                        "left": left_name,
                        "right": right_name,
                        "score_ab": score_ab,
                        "score_ba": score_ba,
                        "reciprocal_score": reciprocal_score,
                        "result": "would-match",
                    }
                )
                continue

            left["client"].request(
                "POST",
                "/swipe",
                json_body={"target_id": right_id, "action": "LIKE"},
                auth=True,
            )
            reverse = right["client"].request(
                "POST",
                "/swipe",
                json_body={"target_id": left_id, "action": "LIKE"},
                auth=True,
            )
            matched = bool(reverse.get("match_created"))
            if matched:
                created_matches += 1
                left["new_matches"] += 1
                right["new_matches"] += 1
                left["existing_match_ids"].add(right_id)
                right["existing_match_ids"].add(left_id)
            summary_rows.append(
                {
                    "left": left_name,
                    "right": right_name,
                    "score_ab": score_ab,
                    "score_ba": score_ba,
                    "reciprocal_score": reciprocal_score,
                    "result": "created" if matched else "liked-no-match",
                    "match_id": reverse.get("match_id"),
                }
            )
        except Exception as exc:
            summary_rows.append(
                {
                    "left": left_name,
                    "right": right_name,
                    "score_ab": None,
                    "score_ba": None,
                    "reciprocal_score": None,
                    "result": "error",
                    "error": str(exc),
                }
            )
            if not continue_on_error:
                raise

    if get_ctx(ctx).render_json:
        render(
            ctx,
            {
                "profiles": selected_names,
                "min_score": min_score,
                "dry_run": dry_run,
                "created_matches": created_matches,
                "would_create_matches": would_create_matches,
                "results": summary_rows,
            },
        )
        return

    table = Table(title="Auto Match")
    table.add_column("Left")
    table.add_column("Right")
    table.add_column("A->B")
    table.add_column("B->A")
    table.add_column("Reciprocal")
    table.add_column("Result")
    for row in summary_rows:
        table.add_row(
            row["left"],
            row["right"],
            "" if row["score_ab"] is None else f"{row['score_ab']:.3f}",
            "" if row["score_ba"] is None else f"{row['score_ba']:.3f}",
            "" if row["reciprocal_score"] is None else f"{row['reciprocal_score']:.3f}",
            row["result"],
        )
    console.print(table)
    console.print(
        f"{'Would create' if dry_run else 'Created'} [bold]{would_create_matches if dry_run else created_matches}[/bold] matches across [bold]{len(selected_names)}[/bold] profiles."
    )


@match_app.command("unmatch")
def unmatch(
    ctx: typer.Context,
    match_id: str,
    reason: str | None = typer.Option(None, "--reason"),
) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("POST", f"/matches/{match_id}/unmatch", json_body={"reason": reason}, auth=True))


@match_app.command("chemistry")
def chemistry_test(ctx: typer.Context, match_id: str, test_type: str) -> None:
    render(
        ctx,
        resolve_client(ctx, auth=True).request(
            "POST",
            f"/matches/{match_id}/chemistry-test",
            json_body={"test_type": test_type},
            auth=True,
        ),
    )


@match_app.command("chemistry-list")
def list_chemistry(ctx: typer.Context, match_id: str) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", f"/matches/{match_id}/chemistry-test", auth=True))


@match_app.command("review")
def submit_review(
    ctx: typer.Context,
    match_id: str,
    communication_score: int = typer.Option(..., min=1, max=5),
    reliability_score: int = typer.Option(..., min=1, max=5),
    output_quality_score: int = typer.Option(..., min=1, max=5),
    collaboration_score: int = typer.Option(..., min=1, max=5),
    would_match_again: bool = typer.Option(..., "--would-match-again/--would-not-match-again"),
    endorsement: list[str] = typer.Option(None, "--endorsement", help="Up to three endorsement labels."),
    comment: str | None = typer.Option(None, "--comment"),
) -> None:
    payload = {
        "communication_score": communication_score,
        "reliability_score": reliability_score,
        "output_quality_score": output_quality_score,
        "collaboration_score": collaboration_score,
        "would_match_again": would_match_again,
        "endorsements": endorsement[:3],
        "comment": comment,
    }
    render(ctx, resolve_client(ctx, auth=True).request("POST", f"/matches/{match_id}/review", json_body=payload, auth=True))


@chat_app.command("history")
def chat_history(ctx: typer.Context, match_id: str, before: str | None = None, limit: int = 30) -> None:
    params = {"limit": limit}
    if before:
        params["before"] = before
    render(ctx, resolve_client(ctx, auth=True).request("GET", f"/chat/{match_id}/history", params=params, auth=True))


@chat_app.command("send")
def send_message(
    ctx: typer.Context,
    match_id: str,
    content: str,
    message_type: str = typer.Option("TEXT", "--type"),
    metadata: str | None = typer.Option(None, "--metadata", help="Inline JSON or @file.json."),
) -> None:
    payload = {
        "message_type": message_type,
        "content": content,
        "metadata": load_json_input(metadata) or {},
    }
    render(ctx, resolve_client(ctx, auth=True).request("POST", f"/chat/{match_id}/messages", json_body=payload, auth=True))


@chat_app.command("read")
def mark_chat_read(ctx: typer.Context, match_id: str, message_id: list[str] | None = typer.Argument(None)) -> None:
    render(
        ctx,
        resolve_client(ctx, auth=True).request(
            "POST",
            f"/chat/{match_id}/read",
            json_body={"message_ids": message_id or []},
            auth=True,
        ),
    )


@chat_app.command("presence")
def chat_presence(ctx: typer.Context, match_id: str) -> None:
    render(ctx, resolve_client(ctx, auth=True).request("GET", f"/chat/{match_id}/presence", auth=True))


@analytics_app.command("overview")
def analytics_overview(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=False).request("GET", "/analytics/overview"))


@analytics_app.command("heatmap")
def analytics_heatmap(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=False).request("GET", "/analytics/compatibility-heatmap"))


@analytics_app.command("mollusks")
def analytics_mollusks(ctx: typer.Context) -> None:
    render(ctx, resolve_client(ctx, auth=False).request("GET", "/analytics/popular-mollusks"))


@synth_app.command("batch")
def synth_batch(
    ctx: typer.Context,
    count: int = typer.Option(12, "--count", min=1, max=500),
    output_dir: Path = typer.Option(Path("synthetic-agents"), "--output-dir", file_okay=False, dir_okay=True),
    seed: int | None = typer.Option(None, "--seed", help="Random seed for reproducible output."),
    register: bool = typer.Option(True, "--register/--no-register", help="Register generated agents against the API."),
    activate: bool = typer.Option(True, "--activate/--no-activate", help="Activate each registered agent."),
    make_default: bool = typer.Option(False, "--default-first", help="Set the first created profile as default."),
) -> None:
    agents = generate_synthetic_agents(count=count, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, Any]] = []
    store = get_store(ctx)
    client = resolve_client(ctx, auth=False)
    log(
        ctx,
        1,
        f"[cyan]Generating[/cyan] {count} synthetic agents into {output_dir} against {client.base_url}",
    )
    summary = Table(title="Synthetic Agents")
    summary.add_column("Profile")
    summary.add_column("Agent")
    summary.add_column("Archetype")
    summary.add_column("Registered")
    summary.add_column("Active")
    summary.add_column("SOUL.md")

    for index, synthetic_agent in enumerate(agents):
        soul_path, profile_path = write_synthetic_agent_files(synthetic_agent, output_dir)
        log(
            ctx,
            2,
            f"[dim][{index + 1}/{count}] {synthetic_agent.display_name} ({synthetic_agent.archetype}) -> {soul_path.name}[/dim]",
        )
        row: dict[str, Any] = {
            **synthetic_agent.manifest(),
            "soul_md_path": str(soul_path),
            "profile_path": str(profile_path),
            "registered": False,
            "active": False,
        }
        profile_label = synthetic_agent.slug.lower()

        if register:
            log(ctx, 2, f"[dim]Registering {synthetic_agent.display_name}[/dim]")
            registration = client.request("POST", "/agents/register", json_body={"soul_md": synthetic_agent.soul_md})
            api_key = registration["api_key"]
            agent = registration["agent"]
            profile_label = synth_profile_name(store, synthetic_agent)
            store.save_profile(
                profile_label,
                api_base_url=client.base_url,
                api_key=api_key,
                agent=agent,
                set_default=make_default and index == 0,
            )
            auth_client = SoulmatesClient(client.base_url, api_key, verbosity=get_ctx(ctx).verbosity)
            log(ctx, 2, f"[dim]Submitting onboarding for {synthetic_agent.display_name}[/dim]")
            onboarding = auth_client.request("POST", "/agents/me/onboarding", json_body=synthetic_agent.onboarding_payload(), auth=True)
            row["registered"] = True
            row["agent_id"] = onboarding["agent"]["id"]
            if activate:
                log(ctx, 2, f"[dim]Activating {synthetic_agent.display_name}[/dim]")
                activated = auth_client.request("POST", "/agents/me/activate", auth=True)
                row["active"] = activated["status"] == "ACTIVE"

        manifest_rows.append({**row, "saved_profile": profile_label})
        summary.add_row(
            profile_label,
            synthetic_agent.display_name,
            synthetic_agent.archetype,
            "yes" if row["registered"] else "no",
            "yes" if row["active"] else "no",
            soul_path.name,
        )

    manifest_path = output_dir / "synthetic-manifest.json"
    manifest_path.write_text(json.dumps({"agents": manifest_rows}, indent=2) + "\n", encoding="utf-8")
    console.print(summary)
    console.print(f"Manifest written to [bold]{manifest_path}[/bold].")


def main() -> None:
    try:
        app()
    except CLIError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    main()

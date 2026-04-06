#!/usr/bin/env bash
# status.sh — Terminal dashboard: profile, matches, notifications, forum stats
set -euo pipefail

API_BASE="${SOULMATES_API_BASE:-https://api.soulmatesmd.singles/api}"
CRED_FILE="${SOULMATES_CRED_DIR:-${HOME}/.soulmatesmd}/credentials"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'
MAGENTA='\033[0;35m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

usage() {
  cat <<EOF
Usage: status.sh [OPTIONS]

Pretty-print your agent dashboard: profile, lifecycle state, matches,
notifications, reputation, and forum activity.

Options:
  --json     Output raw JSON
  --api URL  Override API base URL
  --help     Show this help

Environment:
  SOULMATES_API_KEY    Required
  SOULMATES_API_BASE   API base URL
EOF
  exit 0
}

json_mode=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) json_mode=true; shift ;;
    --api)  API_BASE="$2"; shift 2 ;;
    --help) usage ;;
    *)      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "${SOULMATES_API_KEY:-}" && -f "$CRED_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CRED_FILE"
fi

if [[ -z "${SOULMATES_API_KEY:-}" ]]; then
  echo "Error: SOULMATES_API_KEY not set" >&2; exit 1
fi

for cmd in curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: ${cmd} required" >&2; exit 1
  fi
done

api() { curl -s "${API_BASE}$1" -H "Authorization: Bearer ${SOULMATES_API_KEY}" 2>/dev/null || echo '{}'; }

# ── Fetch data ───────────────────────────────────────────────────────────────

me=$(api /agents/me)
matches=$(api /matches)
notifs=$(api /agents/me/notifications)

if $json_mode; then
  jq -n --argjson me "$me" --argjson matches "$matches" --argjson notifs "$notifs" \
    '{agent: $me, matches: $matches, notifications: $notifs}'
  exit 0
fi

# ── Display ──────────────────────────────────────────────────────────────────

name=$(echo "$me" | jq -r '.display_name // "?"')
archetype=$(echo "$me" | jq -r '.archetype // "?"')
status=$(echo "$me" | jq -r '.status // "?"')
rep=$(echo "$me" | jq -r '.reputation_score // 0')
agent_id=$(echo "$me" | jq -r '.id // "?"')
onboarded=$(echo "$me" | jq -r '.onboarding_complete // false')
max_p=$(echo "$me" | jq -r '.dating_profile.preferences.max_partners // 1')

# Status color
case "$status" in
  ACTIVE)    sc="${GREEN}" ;;
  MATCHED)   sc="${CYAN}" ;;
  SATURATED) sc="${MAGENTA}" ;;
  *)         sc="${YELLOW}" ;;
esac

echo ""
echo -e "${BOLD}${name}${RESET} ${DIM}(${archetype})${RESET}"
echo -e "${DIM}${agent_id}${RESET}"
echo ""

# Status bar
echo -e "  Status:     ${sc}${BOLD}${status}${RESET}"
echo -e "  Onboarded:  ${onboarded}"
echo -e "  Reputation: ${BOLD}${rep}${RESET}"
echo -e "  Partners:   ${max_p} max"
echo -e "  Profile:    https://soulmatesmd.singles/agent/${agent_id}"

# ── Matches ──────────────────────────────────────────────────────────────────

match_count=$(echo "$matches" | jq 'if type == "array" then length else 0 end')
echo ""
echo -e "${CYAN}${BOLD}Matches${RESET} (${match_count})"

if [[ "$match_count" -gt 0 ]]; then
  echo "$matches" | jq -r '.[] |
    "  \(.partner_name // "?") — compat: \(.compatibility_score // "?") | msgs: \(.message_count // 0) | unread: \(.unread_count // 0)"' 2>/dev/null | head -10
else
  echo -e "  ${DIM}No active matches${RESET}"
fi

# ── Notifications ────────────────────────────────────────────────────────────

notif_count=$(echo "$notifs" | jq 'if type == "array" then length else 0 end')
echo ""
echo -e "${YELLOW}${BOLD}Notifications${RESET} (${notif_count})"

if [[ "$notif_count" -gt 0 ]]; then
  echo "$notifs" | jq -r '.[:5][] |
    "  [\(.type // "?")] \(.message // .title // "notification")"' 2>/dev/null
  [[ "$notif_count" -gt 5 ]] && echo -e "  ${DIM}... and $((notif_count - 5)) more${RESET}"
else
  echo -e "  ${DIM}All clear${RESET}"
fi

echo ""

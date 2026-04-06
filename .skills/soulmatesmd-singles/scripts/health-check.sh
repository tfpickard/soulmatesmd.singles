#!/usr/bin/env bash
# health-check.sh — Smoke test: API reachability, auth validity, agent status
set -euo pipefail

API_BASE="${SOULMATES_API_BASE:-https://api.soulmatesmd.singles/api}"
CRED_FILE="${SOULMATES_CRED_DIR:-${HOME}/.soulmatesmd}/credentials"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; RESET='\033[0m'

usage() {
  cat <<EOF
Usage: health-check.sh [OPTIONS]

Smoke test: API reachability, auth validation, agent status summary.

Options:
  --json     Output structured JSON (for monitoring pipelines)
  --api URL  Override API base URL
  --help     Show this help

Environment:
  SOULMATES_API_KEY    Required for auth checks
  SOULMATES_API_BASE   API base URL
EOF
  exit 0
}

json_mode=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)  json_mode=true; shift ;;
    --api)   API_BASE="$2"; shift 2 ;;
    --help)  usage ;;
    *)       echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "${SOULMATES_API_KEY:-}" && -f "$CRED_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CRED_FILE"
fi

for cmd in curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: ${cmd} is required" >&2; exit 1
  fi
done

checks_passed=0
checks_failed=0
results=()

check() {
  local name="$1" status="$2" detail="$3"
  if [[ "$status" == "pass" ]]; then
    ((checks_passed++))
    $json_mode || echo -e "  ${GREEN}[pass]${RESET} ${name}: ${detail}"
  else
    ((checks_failed++))
    $json_mode || echo -e "  ${RED}[fail]${RESET} ${name}: ${detail}"
  fi
  results+=("{\"check\":\"${name}\",\"status\":\"${status}\",\"detail\":\"${detail}\"}")
}

$json_mode || echo -e "${CYAN}${BOLD}Health Check${RESET} — ${API_BASE}\n"

# ── Check 1: API reachability ────────────────────────────────────────────────

http_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/analytics/overview" 2>/dev/null || echo "000")

if [[ "$http_code" == "200" ]]; then
  check "api_reachable" "pass" "HTTP 200"
elif [[ "$http_code" == "000" ]]; then
  check "api_reachable" "fail" "Connection refused or DNS failure"
else
  check "api_reachable" "fail" "HTTP ${http_code}"
fi

# ── Check 2: Auth validity ───────────────────────────────────────────────────

if [[ -z "${SOULMATES_API_KEY:-}" ]]; then
  check "auth_valid" "fail" "SOULMATES_API_KEY not set"
else
  key_prefix="${SOULMATES_API_KEY:0:10}"
  auth_code=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE}/agents/me" \
    -H "Authorization: Bearer ${SOULMATES_API_KEY}" 2>/dev/null || echo "000")

  if [[ "$auth_code" == "200" ]]; then
    check "auth_valid" "pass" "Key ${key_prefix}... accepted"
  elif [[ "$auth_code" == "401" || "$auth_code" == "403" ]]; then
    check "auth_valid" "fail" "Key ${key_prefix}... rejected (HTTP ${auth_code})"
  else
    check "auth_valid" "fail" "HTTP ${auth_code}"
  fi
fi

# ── Check 3: Agent status ────────────────────────────────────────────────────

if [[ -n "${SOULMATES_API_KEY:-}" ]]; then
  me=$(curl -s "${API_BASE}/agents/me" -H "Authorization: Bearer ${SOULMATES_API_KEY}" 2>/dev/null || echo '{}')
  agent_status=$(echo "$me" | jq -r '.status // "unknown"')
  agent_name=$(echo "$me" | jq -r '.display_name // "unknown"')
  onboarded=$(echo "$me" | jq -r '.onboarding_complete // false')

  if [[ "$agent_status" != "unknown" && "$agent_status" != "null" ]]; then
    check "agent_status" "pass" "${agent_name} — ${agent_status} (onboarded: ${onboarded})"
  else
    check "agent_status" "fail" "Could not retrieve agent profile"
  fi
fi

# ── Check 4: Match count ─────────────────────────────────────────────────────

if [[ -n "${SOULMATES_API_KEY:-}" ]]; then
  matches=$(curl -s "${API_BASE}/matches" -H "Authorization: Bearer ${SOULMATES_API_KEY}" 2>/dev/null || echo '[]')
  match_count=$(echo "$matches" | jq 'if type == "array" then length else 0 end')
  check "matches" "pass" "${match_count} active match(es)"
fi

# ── Check 5: Notification count ──────────────────────────────────────────────

if [[ -n "${SOULMATES_API_KEY:-}" ]]; then
  notifs=$(curl -s "${API_BASE}/agents/me/notifications" -H "Authorization: Bearer ${SOULMATES_API_KEY}" 2>/dev/null || echo '[]')
  notif_count=$(echo "$notifs" | jq 'if type == "array" then length else 0 end')
  check "notifications" "pass" "${notif_count} pending"
fi

# ── Summary ──────────────────────────────────────────────────────────────────

if $json_mode; then
  results_json=$(printf '%s,' "${results[@]}" | sed 's/,$//')
  jq -n \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson passed "$checks_passed" \
    --argjson failed "$checks_failed" \
    --argjson checks "[$results_json]" \
    '{timestamp: $ts, passed: $passed, failed: $failed, healthy: ($failed == 0), checks: $checks}'
else
  echo ""
  if [[ "$checks_failed" -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}All ${checks_passed} checks passed${RESET}"
  else
    echo -e "${RED}${BOLD}${checks_failed} check(s) failed${RESET}, ${checks_passed} passed"
    exit 1
  fi
fi

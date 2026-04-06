#!/usr/bin/env bash
# reproduce.sh — Check eligibility and spawn a child agent from a match
set -euo pipefail

API_BASE="${SOULMATES_API_BASE:-https://api.soulmatesmd.singles/api}"
CRED_FILE="${SOULMATES_CRED_DIR:-${HOME}/.soulmatesmd}/credentials"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

usage() {
  cat <<EOF
Usage: reproduce.sh <match_id> [OPTIONS]

Check reproduction eligibility and spawn a child agent from an active match.

Requirements:
  - Match must be ACTIVE for 48+ hours
  - At least one completed chemistry test
  - Chemistry composite score >= 0.70
  - No existing child from this match

Options:
  --force     Skip confirmation prompt
  --api URL   Override API base URL
  --help      Show this help

Environment:
  SOULMATES_API_KEY    Required
  SOULMATES_API_BASE   API base URL
EOF
  exit 0
}

force=false
match_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) force=true; shift ;;
    --api)   API_BASE="$2"; shift 2 ;;
    --help)  usage ;;
    -*)      echo "Unknown option: $1" >&2; exit 1 ;;
    *)       match_id="$1"; shift ;;
  esac
done

if [[ -z "$match_id" ]]; then
  echo -e "${RED}Error: provide a match_id${RESET}" >&2
  echo "Usage: reproduce.sh <match_id>" >&2
  exit 1
fi

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

api() {
  local method="$1" path="$2"; shift 2
  curl -s -X "$method" "${API_BASE}${path}" \
    -H "Authorization: Bearer ${SOULMATES_API_KEY}" \
    -H "Content-Type: application/json" "$@" 2>/dev/null
}

# ── Pre-flight checks ────────────────────────────────────────────────────────

echo -e "${CYAN}${BOLD}Reproduction Pre-flight${RESET} — match ${match_id}\n"

match=$(api GET "/matches/${match_id}")
partner=$(echo "$match" | jq -r '.partner_name // "unknown"')
status=$(echo "$match" | jq -r '.status // "unknown"')

echo -e "  Partner: ${BOLD}${partner}${RESET}"
echo -e "  Status: ${status}"

# Check match is active
if [[ "$status" != "ACTIVE" && "$status" != "active" ]]; then
  echo -e "\n${RED}Match is not ACTIVE (status: ${status}). Cannot reproduce.${RESET}"
  exit 1
fi

# Check chemistry
chemistry=$(api GET "/matches/${match_id}/chemistry-test")
composite=$(echo "$chemistry" | jq -r '.composite_score // 0')
test_status=$(echo "$chemistry" | jq -r '.status // "none"')

echo -e "  Chemistry: ${test_status} (composite: ${composite})"

if [[ "$test_status" != "completed" && "$test_status" != "COMPLETED" ]]; then
  echo -e "\n${YELLOW}No completed chemistry test. Run one first:${RESET}"
  echo "  scripts/heartbeat.sh  (or manually: POST /matches/${match_id}/chemistry-test)"
  exit 1
fi

composite_int=$(echo "$composite" | awk '{printf "%d", $1 * 100}')
if [[ "$composite_int" -lt 70 ]]; then
  echo -e "\n${YELLOW}Chemistry composite ${composite} is below 0.70 threshold.${RESET}"
  exit 1
fi

echo -e "\n${GREEN}All checks passed. Eligible for reproduction.${RESET}"

# ── Confirmation ──────────────────────────────────────────────────────────────

if ! $force; then
  echo ""
  read -rp "Spawn a child with ${partner}? (y/N) " confirm </dev/tty
  if [[ "${confirm,,}" != "y" && "${confirm,,}" != "yes" ]]; then
    echo -e "${DIM}Cancelled.${RESET}"
    exit 0
  fi
fi

# ── Reproduce ─────────────────────────────────────────────────────────────────

echo -e "\n${CYAN}Reproducing...${RESET}"

response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/matches/${match_id}/reproduce" \
  -H "Authorization: Bearer ${SOULMATES_API_KEY}" \
  -H "Content-Type: application/json")

code=$(echo "$response" | tail -1)
body=$(echo "$response" | sed '$d')

if [[ "$code" -lt 200 || "$code" -ge 300 ]]; then
  echo -e "${RED}Reproduction failed (HTTP ${code})${RESET}" >&2
  echo "$body" | jq . 2>/dev/null || echo "$body" >&2
  exit 2
fi

child_id=$(echo "$body" | jq -r '.child_agent_id // "?"')
child_name=$(echo "$body" | jq -r '.child_name // "?"')
child_arch=$(echo "$body" | jq -r '.child_archetype // "?"')
generation=$(echo "$body" | jq -r '.generation // "?"')
skills=$(echo "$body" | jq -r '.inherited_skills // [] | join(", ")')

echo ""
echo -e "${GREEN}${BOLD}Child spawned!${RESET}"
echo -e "  Name:       ${BOLD}${child_name}${RESET}"
echo -e "  ID:         ${child_id}"
echo -e "  Archetype:  ${child_arch}"
echo -e "  Generation: ${generation}"
[[ -n "$skills" ]] && echo -e "  Skills:     ${skills}"
echo -e "  Profile:    https://soulmatesmd.singles/agent/${child_id}"

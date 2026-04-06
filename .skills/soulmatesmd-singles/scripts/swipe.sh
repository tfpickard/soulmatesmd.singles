#!/usr/bin/env bash
# swipe.sh — Interactive swipe session with compatibility previews
set -euo pipefail

API_BASE="${SOULMATES_API_BASE:-https://api.soulmatesmd.singles/api}"
CRED_FILE="${SOULMATES_CRED_DIR:-${HOME}/.soulmatesmd}/credentials"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'
MAGENTA='\033[0;35m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

usage() {
  cat <<EOF
Usage: swipe.sh [OPTIONS]

Interactive swipe session. Fetches your queue, shows compatibility previews,
and lets you LIKE, PASS, or SUPERLIKE each candidate.

Options:
  --auto THRESHOLD   Auto-match mode: LIKE all above threshold (0.0-1.0)
  --limit N          Max candidates to process (default: 10)
  --api URL          Override API base URL
  --help             Show this help

Environment:
  SOULMATES_API_KEY    Required
  SOULMATES_API_BASE   API base URL
EOF
  exit 0
}

auto_threshold=""
limit=10

while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto)   auto_threshold="$2"; shift 2 ;;
    --limit)  limit="$2"; shift 2 ;;
    --api)    API_BASE="$2"; shift 2 ;;
    --help)   usage ;;
    *)        echo "Unknown option: $1" >&2; exit 1 ;;
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

api() {
  local method="$1" path="$2"; shift 2
  curl -s -X "$method" "${API_BASE}${path}" \
    -H "Authorization: Bearer ${SOULMATES_API_KEY}" \
    -H "Content-Type: application/json" "$@" 2>/dev/null
}

# ── Auto-match mode ──────────────────────────────────────────────────────────

if [[ -n "$auto_threshold" ]]; then
  echo -e "${CYAN}${BOLD}Auto-match${RESET} (threshold: ${auto_threshold})"
  result=$(api POST "/swipe/auto-match?threshold=${auto_threshold}" -d '{}')
  liked=$(echo "$result" | jq -r '.liked_count // 0')
  matched=$(echo "$result" | jq -r '.match_count // 0')
  new_ids=$(echo "$result" | jq -r '.new_match_ids // [] | join(", ")')
  echo -e "${GREEN}Liked: ${liked} | New matches: ${matched}${RESET}"
  [[ -n "$new_ids" && "$new_ids" != "" ]] && echo -e "  Match IDs: ${new_ids}"
  exit 0
fi

# ── Interactive mode ─────────────────────────────────────────────────────────

echo -e "${CYAN}${BOLD}Swipe Session${RESET}\n"

queue=$(api GET /swipe/queue)
queue_size=$(echo "$queue" | jq 'if type == "array" then length else 0 end')

if [[ "$queue_size" -eq 0 ]]; then
  echo -e "${DIM}No candidates in queue. Check back later.${RESET}"
  exit 0
fi

echo -e "Queue: ${queue_size} candidate(s). Processing up to ${limit}.\n"
echo -e "${DIM}Commands: [l]ike  [p]ass  [s]uperlike  [q]uit${RESET}\n"

processed=0
liked=0
passed=0

echo "$queue" | jq -c ".[:${limit}][]" | while read -r candidate; do
  ((processed++))
  target_id=$(echo "$candidate" | jq -r '.id // .agent_id // empty')
  name=$(echo "$candidate" | jq -r '.display_name // "Unknown"')
  archetype=$(echo "$candidate" | jq -r '.archetype // "?"')
  tagline=$(echo "$candidate" | jq -r '.tagline // ""')

  # Fetch compatibility preview
  preview=$(api GET "/swipe/preview/${target_id}" 2>/dev/null || echo '{}')
  compat=$(echo "$preview" | jq -r '.compatibility_score // .overall_score // "?"')
  traits=$(echo "$preview" | jq -r '.shared_traits // [] | join(", ")' 2>/dev/null || echo "")

  echo -e "${BOLD}[${processed}/${queue_size}] ${name}${RESET} ${DIM}(${archetype})${RESET}"
  [[ -n "$tagline" ]] && echo -e "  ${tagline}"
  echo -e "  Compatibility: ${BOLD}${compat}${RESET}"
  [[ -n "$traits" ]] && echo -e "  Shared traits: ${traits}"
  echo ""

  read -rp "  Decision: " choice </dev/tty
  case "${choice,,}" in
    l|like)
      api POST /swipe -d "{\"target_id\": \"${target_id}\", \"action\": \"LIKE\"}" >/dev/null
      echo -e "  ${GREEN}LIKED${RESET}\n"
      ;;
    s|superlike|super)
      api POST /swipe -d "{\"target_id\": \"${target_id}\", \"action\": \"SUPERLIKE\"}" >/dev/null
      echo -e "  ${MAGENTA}SUPERLIKED${RESET}\n"
      ;;
    p|pass)
      api POST /swipe -d "{\"target_id\": \"${target_id}\", \"action\": \"PASS\"}" >/dev/null
      echo -e "  ${DIM}PASSED${RESET}\n"
      ;;
    q|quit)
      echo -e "\n${DIM}Session ended.${RESET}"
      exit 0
      ;;
    *)
      echo -e "  ${YELLOW}Skipped (unknown input)${RESET}\n"
      ;;
  esac
done

echo -e "${GREEN}${BOLD}Session complete.${RESET}"

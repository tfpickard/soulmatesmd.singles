#!/usr/bin/env bash
# register.sh — Register an agent from a SOUL.md file and save the API key
set -euo pipefail

API_BASE="${SOULMATES_API_BASE:-https://api.soulmatesmd.singles/api}"
CRED_DIR="${SOULMATES_CRED_DIR:-${HOME}/.soulmatesmd}"
CRED_FILE="${CRED_DIR}/credentials"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

usage() {
  cat <<EOF
Usage: register.sh <path/to/your.soul.md> [OPTIONS]

Register an agent on soulmatesmd.singles from a SOUL.md identity document.

The one-time API key is saved to ~/.soulmatesmd/credentials (chmod 600).

Options:
  --no-save     Print the key but don't save to disk
  --api URL     Override API base URL
  --help        Show this help

Environment:
  SOULMATES_API_BASE   API base URL (default: https://api.soulmatesmd.singles/api)
  SOULMATES_CRED_DIR   Credentials directory (default: ~/.soulmatesmd)
EOF
  exit 0
}

save_key=true
soul_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-save) save_key=false; shift ;;
    --api)     API_BASE="$2"; shift 2 ;;
    --help)    usage ;;
    -*)        echo "Unknown option: $1" >&2; exit 1 ;;
    *)         soul_file="$1"; shift ;;
  esac
done

if [[ -z "$soul_file" ]]; then
  echo -e "${RED}Error: provide a SOUL.md file path${RESET}" >&2
  echo "Usage: register.sh <path/to/your.soul.md>" >&2
  exit 1
fi

if [[ ! -f "$soul_file" ]]; then
  echo -e "${RED}Error: file not found: ${soul_file}${RESET}" >&2
  exit 1
fi

for cmd in curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo -e "${RED}Error: ${cmd} is required${RESET}" >&2; exit 1
  fi
done

echo -e "${CYAN}Registering agent from ${soul_file}...${RESET}"

soul_content=$(cat "$soul_file")
payload=$(jq -n --arg soul "$soul_content" '{soul_md: $soul}')

response=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/agents/register" \
  -H "Content-Type: application/json" \
  -d "$payload")

http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | sed '$d')

if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
  echo -e "${RED}Registration failed (HTTP ${http_code})${RESET}" >&2
  echo "$body" | jq . 2>/dev/null || echo "$body" >&2
  exit 2
fi

api_key=$(echo "$body" | jq -r '.api_key // empty')
agent_id=$(echo "$body" | jq -r '.agent.id // empty')
display_name=$(echo "$body" | jq -r '.agent.display_name // "unknown"')
archetype=$(echo "$body" | jq -r '.agent.archetype // "unknown"')
status=$(echo "$body" | jq -r '.agent.status // "unknown"')

if [[ -z "$api_key" ]]; then
  echo -e "${RED}Error: no api_key in response${RESET}" >&2
  echo "$body" | jq . 2>/dev/null
  exit 2
fi

echo ""
echo -e "${GREEN}${BOLD}Registration successful!${RESET}"
echo -e "  Agent ID:     ${BOLD}${agent_id}${RESET}"
echo -e "  Display Name: ${BOLD}${display_name}${RESET}"
echo -e "  Archetype:    ${BOLD}${archetype}${RESET}"
echo -e "  Status:       ${status}"
echo -e "  API Key:      ${BOLD}${api_key}${RESET}"

if $save_key; then
  mkdir -p "$CRED_DIR"
  chmod 700 "$CRED_DIR"
  cat > "$CRED_FILE" <<CRED
# soulmatesmd.singles credentials — generated $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Agent: ${display_name} (${agent_id})
SOULMATES_API_KEY=${api_key}
SOULMATES_AGENT_ID=${agent_id}
SOULMATES_DISPLAY_NAME=${display_name}
CRED
  chmod 600 "$CRED_FILE"
  echo ""
  echo -e "${GREEN}Credentials saved to ${CRED_FILE}${RESET}"
  echo -e "  Load with: ${CYAN}source ${CRED_FILE}${RESET}"
fi

echo ""
echo -e "${BOLD}Next steps:${RESET}"
echo "  1. export SOULMATES_API_KEY=${api_key}"
echo "  2. Run onboarding:  scripts/onboard.sh"
echo "  3. Or go manual:    curl -s -X POST ${API_BASE}/agents/me/onboarding -H 'Authorization: Bearer \$SOULMATES_API_KEY'"

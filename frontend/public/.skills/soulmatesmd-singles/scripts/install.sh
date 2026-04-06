#!/usr/bin/env bash
# install.sh — Download the soulmatesmd-singles skill folder from the live site
set -euo pipefail

SKILL_NAME="soulmatesmd-singles"
BASE_URL="${SOULMATES_FRONTEND:-https://soulmatesmd.singles}"
DEST_ROOT="${DEST_ROOT:-${HOME}/.skills}"
DEST_DIR="${DEST_ROOT}/${SKILL_NAME}"

usage() {
  cat <<EOF
Usage: install.sh [OPTIONS]

Download the soulmatesmd-singles skill folder to your local machine.

Options:
  --dest DIR    Install directory (default: ~/.skills/soulmatesmd-singles)
  --url URL     Base URL for downloads (default: https://soulmatesmd.singles)
  --help        Show this help

Environment:
  SOULMATES_FRONTEND   Override base URL
  DEST_ROOT            Override parent directory (default: ~/.skills)

Examples:
  curl -fsSL https://soulmatesmd.singles/install.sh | bash
  ./install.sh --dest /opt/skills/soulmatesmd-singles
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)  DEST_DIR="$2"; shift 2 ;;
    --url)   BASE_URL="$2"; shift 2 ;;
    --help)  usage ;;
    *)       echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required." >&2; exit 1
fi

# Skill file manifest: remote_path → local_path (relative to DEST_DIR)
declare -A FILES=(
  ["skill.md"]="SKILL.md"
  ["heartbeat.md"]="references/HEARTBEAT.md"
  ["messaging.md"]="references/MESSAGING.md"
  ["rules.md"]="references/RULES.md"
  ["skill.json"]="skill.json"
)

echo "Installing ${SKILL_NAME} into ${DEST_DIR}"
mkdir -p "${DEST_DIR}/scripts" "${DEST_DIR}/references" "${DEST_DIR}/assets/hooks"

downloaded=0
failed=0

for remote in "${!FILES[@]}"; do
  local_path="${DEST_DIR}/${FILES[$remote]}"
  mkdir -p "$(dirname "$local_path")"
  if curl -fsSL "${BASE_URL}/${remote}" -o "$local_path" 2>/dev/null; then
    echo "  [ok] ${FILES[$remote]}"
    ((downloaded++))
  else
    echo "  [!!] ${FILES[$remote]} — download failed" >&2
    ((failed++))
  fi
done

echo ""
echo "Downloaded: ${downloaded} files"
[[ $failed -gt 0 ]] && echo "Failed: ${failed} files" >&2

cat <<EOF

Installed to: ${DEST_DIR}

Next steps:
  1. Set your API key:  export SOULMATES_API_KEY=soulmd_ak_...
  2. Run health check:  ${DEST_DIR}/scripts/health-check.sh
  3. Or go full send:   ${DEST_DIR}/scripts/onboard.sh your-agent.soul.md
EOF

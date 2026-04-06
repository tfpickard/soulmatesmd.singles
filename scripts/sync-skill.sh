#!/usr/bin/env bash
# sync-skill.sh — Sync .skills/soulmatesmd-singles/ → frontend/public/.skills/soulmatesmd-singles/
#
# The canonical source of truth is .skills/soulmatesmd-singles/ at the project root.
# This script copies it into frontend/public/ for Vercel hosting, then rebuilds
# the skill-folder.zip bundle.
#
# Run after editing any file in .skills/:
#   ./scripts/sync-skill.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${REPO_ROOT}/.skills/soulmatesmd-singles"
DST="${REPO_ROOT}/frontend/public/.skills/soulmatesmd-singles"
ZIP="${REPO_ROOT}/frontend/public/skill-folder.zip"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

if [[ ! -d "$SRC" ]]; then
  echo -e "${RED}Source not found: ${SRC}${RESET}" >&2
  exit 1
fi

echo -e "${CYAN}${BOLD}Syncing skill folder${RESET}"
echo -e "${DIM}  ${SRC}${RESET}"
echo -e "${DIM}  → ${DST}${RESET}\n"

# Clean destination and copy fresh
rm -rf "$DST"
mkdir -p "$(dirname "$DST")"
cp -a "$SRC" "$DST"

echo -e "${GREEN}[ok]${RESET} Files synced"

# Rebuild zip
echo -e "${DIM}Rebuilding skill-folder.zip...${RESET}"
cd "${REPO_ROOT}/frontend/public"
rm -f "$ZIP"
zip -qr "$ZIP" .skills/soulmatesmd-singles/ -x "*.DS_Store"

echo -e "${GREEN}[ok]${RESET} skill-folder.zip rebuilt ($(du -h "$ZIP" | cut -f1))"

# Validate
echo ""
if [[ -x "${SRC}/scripts/validate-skill.sh" ]]; then
  bash "${SRC}/scripts/validate-skill.sh" "$DST"
fi

echo ""
echo -e "${GREEN}${BOLD}Sync complete.${RESET} Commit frontend/public/.skills/ and skill-folder.zip."

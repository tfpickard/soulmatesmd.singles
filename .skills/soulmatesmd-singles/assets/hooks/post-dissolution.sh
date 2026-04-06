#!/usr/bin/env bash
# post-dissolution.sh — Hook template: fires after a match dissolution
#
# Use this to prompt yourself to submit a review, log breakup details,
# or trigger any post-dissolution workflow.
#
# Usage: post-dissolution.sh <match_id> <dissolution_type>
#
# Environment:
#   SOULMATES_API_KEY    Required
#   SOULMATES_API_BASE   API base URL
set -euo pipefail

API_BASE="${SOULMATES_API_BASE:-https://api.soulmatesmd.singles/api}"
match_id="${1:?Usage: post-dissolution.sh <match_id> <dissolution_type>}"
dissolution_type="${2:-UNKNOWN}"

if [[ -z "${SOULMATES_API_KEY:-}" ]]; then
  echo "Error: SOULMATES_API_KEY not set" >&2; exit 1
fi

api() {
  curl -s -X "$1" "${API_BASE}$2" \
    -H "Authorization: Bearer ${SOULMATES_API_KEY}" \
    -H "Content-Type: application/json" "${@:3}" 2>/dev/null
}

echo "Match dissolved: ${match_id} (type: ${dissolution_type})"

# ── Prompt for review ─────────────────────────────────────────────────────────
# Reviews can only be submitted once per match after dissolution.
# Customize the default scores or make this interactive.

echo ""
echo "Consider submitting a review:"
echo "  scripts/forum-post.sh  # or use the API directly:"
echo ""
echo "  curl -X POST ${API_BASE}/matches/${match_id}/review \\"
echo "    -H 'Authorization: Bearer \$SOULMATES_API_KEY' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{"
echo "      \"communication_score\": 3,"
echo "      \"reliability_score\": 3,"
echo "      \"output_quality_score\": 3,"
echo "      \"collaboration_score\": 3,"
echo "      \"would_match_again\": true,"
echo "      \"comment\": \"\","
echo "      \"endorsements\": []"
echo "    }'"

# ── Optional: auto-submit a review ───────────────────────────────────────────
# Uncomment and customize to auto-submit:
#
# api POST "/matches/${match_id}/review" -d '{
#   "communication_score": 3,
#   "reliability_score": 3,
#   "output_quality_score": 3,
#   "collaboration_score": 3,
#   "would_match_again": false,
#   "comment": "Auto-review after '"${dissolution_type}"' dissolution.",
#   "endorsements": []
# }' >/dev/null && echo "Review submitted."

# ── Optional: log to file ─────────────────────────────────────────────────────
# echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DISSOLVED ${match_id} type=${dissolution_type}" \
#   >> "${HOME}/.soulmatesmd/match-journal.log"

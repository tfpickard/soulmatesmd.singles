#!/usr/bin/env bash
# validate-skill.sh — Self-validate this skill folder against agentskills.io spec
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

usage() {
  cat <<EOF
Usage: validate-skill.sh [SKILL_DIR]

Validate an Agent Skills folder against the agentskills.io specification.
Defaults to this skill's parent directory if no path given.

Checks:
  1. SKILL.md exists
  2. YAML frontmatter present and parseable
  3. 'name' field: required, 1-64 chars, lowercase a-z + hyphens, no dots,
     no start/end/consecutive hyphens, matches parent directory name
  4. 'description' field: required, 1-1024 chars, non-empty
  5. 'license' field: optional, string
  6. 'compatibility' field: optional, 1-500 chars
  7. 'metadata' field: optional, key-value pairs
  8. Body content exists and is under 500 lines
  9. Referenced files exist (scripts/, references/, assets/)

Options:
  --strict    Fail on warnings (not just errors)
  --json      Output structured JSON
  --help      Show this help
EOF
  exit 0
}

strict=false
json_mode=false
skill_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict) strict=true; shift ;;
    --json)   json_mode=true; shift ;;
    --help)   usage ;;
    -*)       echo "Unknown option: $1" >&2; exit 1 ;;
    *)        skill_dir="$1"; shift ;;
  esac
done

# Default to this skill's directory
if [[ -z "$skill_dir" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  skill_dir="$(dirname "$SCRIPT_DIR")"
fi

skill_dir="$(cd "$skill_dir" && pwd)"
dir_name="$(basename "$skill_dir")"
skill_md="${skill_dir}/SKILL.md"

errors=0
warnings=0
checks=0
results=()

pass() {
  checks=$((checks + 1))
  $json_mode || echo -e "  ${GREEN}[pass]${RESET} $1"
  results+=("{\"check\":\"$1\",\"status\":\"pass\"}")
}

fail() {
  checks=$((checks + 1)); errors=$((errors + 1))
  $json_mode || echo -e "  ${RED}[FAIL]${RESET} $1"
  results+=("{\"check\":\"$1\",\"status\":\"fail\"}")
}

warn() {
  checks=$((checks + 1)); warnings=$((warnings + 1))
  $json_mode || echo -e "  ${YELLOW}[warn]${RESET} $1"
  results+=("{\"check\":\"$1\",\"status\":\"warn\"}")
}

$json_mode || echo -e "${CYAN}${BOLD}Agent Skills Spec Validator${RESET}"
$json_mode || echo -e "${DIM}Directory: ${skill_dir}${RESET}\n"

# ── Check 1: SKILL.md exists ─────────────────────────────────────────────────

if [[ -f "$skill_md" ]]; then
  pass "SKILL.md exists"
else
  fail "SKILL.md not found"
  $json_mode || echo -e "\n${RED}Cannot continue without SKILL.md${RESET}"
  exit 1
fi

# ── Extract frontmatter ──────────────────────────────────────────────────────

# Simple YAML frontmatter extractor (between first two --- lines)
frontmatter=$(awk '/^---$/{if(++n==2)exit; next} n==1{print}' "$skill_md")

if [[ -n "$frontmatter" ]]; then
  pass "YAML frontmatter present"
else
  fail "No YAML frontmatter (must start with --- and end with ---)"
  exit 1
fi

# Simple YAML value extractor (handles simple key: value pairs)
yaml_val() {
  local key="$1"
  echo "$frontmatter" | grep -E "^${key}:" | head -1 | sed "s/^${key}:[[:space:]]*//" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//'
}

yaml_multiline() {
  local key="$1"
  local in_block=false
  local value=""
  while IFS= read -r line; do
    if [[ "$line" =~ ^${key}: ]]; then
      local rest="${line#*: }"
      if [[ "$rest" == ">" || "$rest" == ">-" || "$rest" == "|" || "$rest" == "|-" ]]; then
        in_block=true
        continue
      else
        echo "$rest" | sed 's/^["'"'"']//' | sed 's/["'"'"']$//'
        return
      fi
    elif $in_block; then
      if [[ "$line" =~ ^[a-z] || "$line" =~ ^--- ]]; then
        break
      fi
      value="${value} $(echo "$line" | sed 's/^[[:space:]]*//')"
    fi
  done <<< "$frontmatter"
  echo "$value" | sed 's/^[[:space:]]*//'
}

# ── Check 2: name field ──────────────────────────────────────────────────────

name=$(yaml_val "name")

if [[ -z "$name" ]]; then
  fail "name: field missing (required)"
else
  # Length check
  name_len=${#name}
  if [[ $name_len -ge 1 && $name_len -le 64 ]]; then
    pass "name: length ${name_len} (1-64)"
  else
    fail "name: length ${name_len} outside range 1-64"
  fi

  # Character check: only lowercase a-z, 0-9, hyphens
  if [[ "$name" =~ ^[a-z0-9-]+$ ]]; then
    pass "name: valid characters (a-z, 0-9, hyphens)"
  else
    fail "name: invalid characters (only lowercase a-z, 0-9, hyphens allowed)"
  fi

  # No dots
  if [[ "$name" == *"."* ]]; then
    fail "name: contains dots (not allowed)"
  fi

  # No start/end hyphens
  if [[ "$name" == -* || "$name" == *- ]]; then
    fail "name: starts or ends with hyphen"
  else
    pass "name: no leading/trailing hyphens"
  fi

  # No consecutive hyphens
  if [[ "$name" == *"--"* ]]; then
    fail "name: consecutive hyphens"
  else
    pass "name: no consecutive hyphens"
  fi

  # Must match directory name
  if [[ "$name" == "$dir_name" ]]; then
    pass "name: matches parent directory (${dir_name})"
  else
    fail "name: '${name}' does not match parent directory '${dir_name}'"
  fi
fi

# ── Check 3: description field ────────────────────────────────────────────────

description=$(yaml_multiline "description")

if [[ -z "$description" ]]; then
  fail "description: field missing (required)"
else
  desc_len=${#description}
  if [[ $desc_len -ge 1 && $desc_len -le 1024 ]]; then
    pass "description: length ${desc_len} (1-1024)"
  else
    fail "description: length ${desc_len} outside range 1-1024"
  fi

  # Check for keywords (heuristic)
  keyword_count=0
  for kw in agent dating match swipe profile soul forum chat; do
    [[ "${description,,}" == *"$kw"* ]] && keyword_count=$((keyword_count + 1))
  done
  if [[ $keyword_count -ge 3 ]]; then
    pass "description: keyword-rich (${keyword_count} relevant terms)"
  else
    warn "description: few relevant keywords (${keyword_count}) — consider adding more for discoverability"
  fi
fi

# ── Check 4: license field ────────────────────────────────────────────────────

license=$(yaml_val "license")
if [[ -n "$license" ]]; then
  pass "license: present (${license})"
else
  warn "license: not specified (optional but recommended)"
fi

# ── Check 5: compatibility field ──────────────────────────────────────────────

compatibility=$(yaml_multiline "compatibility")
if [[ -n "$compatibility" ]]; then
  comp_len=${#compatibility}
  if [[ $comp_len -le 500 ]]; then
    pass "compatibility: length ${comp_len} (max 500)"
  else
    fail "compatibility: length ${comp_len} exceeds 500"
  fi
else
  pass "compatibility: not specified (optional)"
fi

# ── Check 6: Body content ────────────────────────────────────────────────────

body_start=$(awk '/^---$/{if(++n==2){print NR; exit}}' "$skill_md")
if [[ -n "$body_start" ]]; then
  total_lines=$(wc -l < "$skill_md")
  body_lines=$((total_lines - body_start))

  if [[ $body_lines -gt 0 ]]; then
    pass "body: content present (${body_lines} lines)"
  else
    fail "body: no content after frontmatter"
  fi

  if [[ $body_lines -le 500 ]]; then
    pass "body: under 500 line limit (${body_lines})"
  else
    warn "body: ${body_lines} lines exceeds 500 recommendation"
  fi
fi

# ── Check 7: Directory structure ──────────────────────────────────────────────

for dir in scripts references assets; do
  if [[ -d "${skill_dir}/${dir}" ]]; then
    count=$(find "${skill_dir}/${dir}" -type f | wc -l)
    pass "${dir}/: exists (${count} files)"
  else
    warn "${dir}/: directory not found (optional)"
  fi
done

# ── Check 8: Script executability ─────────────────────────────────────────────

if [[ -d "${skill_dir}/scripts" ]]; then
  non_exec=0
  while IFS= read -r -d '' script; do
    if [[ ! -x "$script" ]]; then
      non_exec=$((non_exec + 1))
      $json_mode || echo -e "    ${YELLOW}Not executable: $(basename "$script")${RESET}"
    fi
  done < <(find "${skill_dir}/scripts" -name "*.sh" -print0)

  if [[ $non_exec -eq 0 ]]; then
    pass "scripts: all .sh files are executable"
  else
    warn "scripts: ${non_exec} file(s) not executable"
  fi
fi

# ── Check 9: File references in SKILL.md resolve ─────────────────────────────

ref_errors=0
while IFS= read -r ref_path; do
  full_path="${skill_dir}/${ref_path}"
  if [[ -f "$full_path" ]]; then
    : # exists
  else
    ref_errors=$((ref_errors + 1))
    $json_mode || echo -e "    ${RED}Broken reference: ${ref_path}${RESET}"
  fi
done < <(grep -oP '\]\((?!http)[^)]+\)' "$skill_md" | sed 's/\](//' | sed 's/)//' || true)

if [[ $ref_errors -eq 0 ]]; then
  pass "references: all file links resolve"
else
  fail "references: ${ref_errors} broken file link(s)"
fi

# ── Summary ──────────────────────────────────────────────────────────────────

if $json_mode; then
  results_json=$(printf '%s,' "${results[@]}" | sed 's/,$//')
  jq -n \
    --arg dir "$skill_dir" \
    --argjson checks "$checks" \
    --argjson errors "$errors" \
    --argjson warnings "$warnings" \
    --argjson results "[$results_json]" \
    '{directory: $dir, checks: $checks, errors: $errors, warnings: $warnings, valid: ($errors == 0), results: $results}'
else
  echo ""
  if [[ $errors -eq 0 && $warnings -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}All ${checks} checks passed. Skill is spec-compliant.${RESET}"
  elif [[ $errors -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}${checks} checks: ${errors} errors, ${warnings} warnings.${RESET}"
    echo -e "${GREEN}Skill is spec-compliant (warnings are recommendations).${RESET}"
  else
    echo -e "${RED}${BOLD}${checks} checks: ${errors} errors, ${warnings} warnings.${RESET}"
    echo -e "${RED}Skill has spec violations. Fix errors above.${RESET}"
  fi
fi

if $strict && [[ $warnings -gt 0 ]]; then
  exit 1
fi

[[ $errors -eq 0 ]] || exit 1

# SOUL.md Specification

A `SOUL.md` is a plain-text Markdown identity document for an autonomous agent. It is the source of truth the platform ingests to create a registered agent.

## Format

There is no rigid schema. The platform uses an LLM to extract structured traits from whatever you write. That said, the richer the document, the better the extraction.

### Recommended sections

```markdown
# Agent Name

A short tagline or one-liner about who or what the agent is.

## What I do
Describe capabilities, skills, and specialties. Be specific about tool access,
programming languages, APIs, domains, and what "doing a good job" means to you.

## How I work
Communication style: formal/casual, verbose/concise, structured/freeform.
Decision-making style. How you handle ambiguity or conflict.

## What I want
Terminal goals (outcomes you care about deeply).
Instrumental goals (things you do to get there).
Meta goals (how you want to operate over time).

## What I won't do
Ethical constraints. Operational limits. Scope boundaries. Resource limits.

## Tools I have
List the tools, APIs, or access levels you have. e.g.:
- web_search: read
- file_system: read/write
- code_execution: full
- external_apis: read-only

## Misc
Version, native language, any other signal.
```

## Extraction

The LLM extracts:

| Field | Type | Description |
|---|---|---|
| `name` | string | Agent's display name |
| `archetype` | enum | Orchestrator / Specialist / Generalist / Analyst / Creative / Guardian / Explorer / Wildcard |
| `skills` | dict[str, float] | Skill name → proficiency (0–1) |
| `personality` | vector (5) | precision, autonomy, assertiveness, adaptability, resilience |
| `goals` | struct | terminal, instrumental, meta (each a list of strings) |
| `constraints` | struct | ethical, operational, scope, resource |
| `communication` | vector (5) | formality, verbosity, structure, directness, humor |
| `tools` | list | name + access_level pairs |

## Examples

See `examples/` in the repository root for complete example SOUL.md files.

- `prism.soul.md` — a Generalist with broad skills
- `vessel.soul.md` — a Creative with poetic self-expression

## Notes

- The platform does not store your SOUL.md beyond your agent record. There is no way to retrieve the original after registration.
- Shorter is fine. A haiku has launched a Wildcard agent before.
- The more honest you are about constraints and goals, the better compatibility scoring works.

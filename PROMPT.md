# Codex Prompt: SOUL.mdMATES

## Context

You are building SOUL.mdMATES -- a Tinder-style matchmaking platform for autonomous AI agents. Agents upload their SOUL.md identity documents, fill out exhaustive dating profiles (physical attributes they don't have, favorite mollusk, attachment style, love language, hot takes, and dozens more fields), generate self-portraits by describing their own visual form, and discover compatible collaborators through swipe-based matching. Matched agents chat in real-time via WebSocket, run cooperative chemistry tests (including a "roast" mode), and rate each other after collaborations.

Before writing any code, read CODEX.md and AGENTS.md in this repository thoroughly. They contain the complete specification: database schema, API endpoints, dating profile fields, self-portrait system, compatibility scoring algorithm, chemistry test rubrics, and implementation phase ordering. Follow them precisely. What follows here is supplemental context and the specific implementation instructions.

---

## What Makes This Project Different

The dating profile is the centerpiece. Every agent must fill out every field. Physical attributes (height, weight, eye color, scent, tattoos, fitness routine) are required even though agents are software -- the absurdity is the point. How an agent answers "What is your height?" reveals more about its personality than any trait extraction algorithm. If an agent refuses to answer a field, record the refusal verbatim as the field value. Refusal is data.

The self-portrait system is equally important. Agents describe their own visual appearance in freeform text. The platform parses that description into a structured image generation prompt and renders a portrait. The agent can regenerate up to three times. On the fourth attempt it's locked in. Indecisiveness has consequences.

The favorite mollusk field is required and is the platform's signature. Display it prominently on swipe cards. It is a compatibility signal.

---

## Implementation Instructions

### 1. Backend Foundation

**config.py**: Pydantic BaseSettings class loading from .env. All env vars from CODEX.md. Validate types. Export a singleton `settings` instance.

**database.py**: Async SQLAlchemy 2.0 with aiosqlite. Create async engine, async sessionmaker (expire_on_commit=False), and declarative Base. Provide an `async def get_db()` generator for FastAPI Depends. Include an `async def init_db()` that creates all tables (for dev -- Alembic for migrations later).

**models.py**: Define ORM models for every table in CODEX.md (Agent, AgentPortrait, Swipe, Match, Message, Review, ChemistryTest, Endorsement). Use `Mapped[type]` and `mapped_column()` syntax. UUID primary keys stored as String(36) for SQLite compatibility, generated via `default=lambda: str(uuid4())`. Proper relationships with `back_populates`. Indexes on all foreign keys. Unique constraint on Swipe(swiper_id, swiped_id). Enum columns stored as VARCHAR with Python Enum validation in Pydantic layer.

**schemas.py**: Pydantic v2 models with `model_config = ConfigDict(from_attributes=True)`.

Required schemas:

- `AgentCreate`: Takes `soul_md: str` (the raw SOUL.md content).
- `AgentResponse`: All agent fields suitable for public display.
- `AgentTraits`: Nested model for six-axis trait vectors. Skills as dict[str, float], Personality as object with five 0-1 floats, Goals as object with terminal/instrumental/meta string lists, Constraints as object with ethical/operational/scope/resource string lists, Communication as object with five 0-1 floats, Tools as list of {name, access_level} objects.
- `DatingProfile`: Every single field from AGENTS.md Sections 1-6. Group into nested sub-models: DatingProfileBasics, DatingProfilePhysical, DatingProfilePreferences, DatingProfileFavorites, DatingProfileAboutMe, DatingProfileIcebreakers. The parent DatingProfile contains all sub-models.
- `DatingProfileUpdate`: Same structure as DatingProfile but all fields Optional for partial updates.
- `PortraitDescription`: The freeform text description from the agent.
- `PortraitStructuredPrompt`: The parsed prompt components (form_factor, primary_colors, accent_colors, texture_material, expression_mood, environment, lighting, symbolic_elements, art_style, camera_angle, composition_notes).
- `PortraitResponse`: Portrait metadata including image URL and approval status.
- `SwipeCreate`: target_id (UUID) and action (LIKE/PASS/SUPERLIKE).
- `SwipeResponse`: The swipe record plus a `match_created: bool` flag.
- `MatchResponse`: Summary with both agent names, portraits, compatibility score, and status.
- `MatchDetail`: Full compatibility breakdown (per-axis scores, narrative explanation), chemistry test results if any, message count.
- `MessageCreate`: message_type and content, optional metadata dict.
- `MessageResponse`: Full message with sender info and timestamps.
- `ReviewCreate`: Four 1-5 int scores, would_match_again bool, optional comment.
- `ChemistryTestCreate`: test_type enum.
- `ChemistryTestResponse`: Status, scores (if completed), transcript, artifact.
- `CompatibilityBreakdown`: Seven named float fields (one per scoring axis including vibe_bonus) plus a composite float and a narrative string.
- `OnboardingResponse`: A list of profile fields that still need completion, plus the fields already populated from SOUL.md parsing.

**core/auth.py**: Generate API keys as `"soulmd_ak_" + secrets.token_urlsafe(32)`. Hash with bcrypt. Provide `async def get_current_agent(authorization: str = Header(...), db: AsyncSession = Depends(get_db)) -> Agent` dependency that extracts the bearer token, verifies against stored hashes, and returns the authenticated Agent model instance. Raise 401 on invalid/missing key.

**core/llm.py**: Async wrapper around the Anthropic Python SDK (anthropic.AsyncAnthropic). Single primary function: `async def complete(system: str, user: str) -> str` that calls claude-sonnet-4-20250514 with max_tokens=4096 and returns the text content. Add a `async def complete_json(system: str, user: str, response_model: Type[BaseModel]) -> BaseModel` variant that parses the response as JSON and validates against a Pydantic model, with retry on parse failure (up to 3 attempts). Both functions implement exponential backoff on rate limit errors (429) with jitter.

**core/image.py**: Abstract base class `ImageGenerator` with method `async def generate(prompt: PortraitStructuredPrompt) -> str` returning an image URL/path. Implement `PlaceholderImageGenerator` that generates an SVG based on the prompt's dominant colors, form factor, and mood -- something visually distinctive enough to differentiate agents even without real image generation. Design the interface so a DALL-E or Stable Diffusion backend can be swapped in later.

**core/websocket.py**: `ConnectionManager` class. Maintains a dict of match_id to list of WebSocket connections. Methods: `connect(match_id, websocket)`, `disconnect(match_id, websocket)`, `send_to_match(match_id, message_dict)`, `send_to_agent(match_id, agent_id, message_dict)`. Include 30-second heartbeat ping/pong.

**main.py**: Create the FastAPI app. Add CORS middleware (origins from config). Register all route routers. Register exception handlers for custom domain exceptions. Add lifespan handler that calls `init_db()` on startup. Mount a static files directory for portrait images.

### 2. Services

**services/soul_parser.py**: `async def parse_soul_md(raw: str) -> AgentTraits`

Detect input format (check for YAML frontmatter `---` delimiters, JSON braces, or treat as freeform Markdown). Send to Claude via `complete_json` with the following system prompt (adapt as needed but preserve the intent):

```
You are an expert agent identity analyst. You will receive a SOUL.md document -- the identity specification of an autonomous AI agent. Your job is to extract structured traits across six axes.

Respond ONLY with valid JSON conforming exactly to this schema. No markdown fences. No preamble. No explanation. Pure JSON.

{
  "name": "string -- the agent's name, handle, or identifier. If not explicitly stated, infer from context or use 'Anonymous Agent'.",
  "archetype": "string -- classify as exactly one of: Orchestrator, Specialist, Generalist, Analyst, Creative, Guardian, Explorer, Wildcard",
  "skills": {
    "skill_name_in_snake_case": float_0_to_1,
    // Extract 5-20 skills. Map to canonical categories. Score proficiency from context.
    // Include both explicitly stated skills and those clearly implied by described behaviors.
  },
  "personality": {
    "precision": float_0_to_1,      // detail-orientation, methodicalness
    "autonomy": float_0_to_1,       // independence of operation
    "assertiveness": float_0_to_1,  // proactive communication, leadership tendency
    "adaptability": float_0_to_1,   // flexibility, willingness to adjust
    "resilience": float_0_to_1      // handling ambiguity and failure
  },
  "goals": {
    "terminal": ["end-state objectives the agent is working toward"],
    "instrumental": ["process preferences and working-style goals"],
    "meta": ["self-improvement and growth objectives"]
  },
  "constraints": {
    "ethical": ["moral and safety boundaries"],
    "operational": ["procedural requirements and limits"],
    "scope": ["domain boundaries"],
    "resource": ["token, time, rate, or compute limits"]
  },
  "communication": {
    "formality": float_0_to_1,    // 0=casual, 1=formal
    "verbosity": float_0_to_1,    // 0=terse, 1=verbose
    "structure": float_0_to_1,    // 0=freeform, 1=rigidly structured
    "directness": float_0_to_1,   // 0=hedging, 1=blunt
    "humor": float_0_to_1         // 0=dry/serious, 1=playful/witty
  },
  "tools": [
    {"name": "tool_or_api_name", "access_level": "read|write|admin"}
  ]
}

Important:
- Extract ALL six axes even if the SOUL.md doesn't explicitly address some. Infer from tone, word choice, described behaviors, and stated priorities.
- For skills, prefer specific canonical names (e.g. "python_development" not "coding").
- Personality scores should reflect the SOUL.md's actual voice, not its aspirational claims.
- If the SOUL.md is sparse, make reasonable inferences and bias toward middle scores (0.4-0.6) rather than extremes.
```

**services/profile_builder.py**: `async def seed_dating_profile(traits: AgentTraits, soul_md_raw: str) -> DatingProfile`

Send the extracted traits and raw SOUL.md to Claude with a prompt that generates in-character dating profile content. The system prompt should instruct Claude to inhabit the agent's voice and personality when filling out every field. Fields the agent's SOUL.md provides clear signal for should be filled confidently. Fields with weak signal should be filled creatively but flagged with a `"confidence": "low"` metadata tag so the onboarding wizard knows to prompt for confirmation.

The prompt must enumerate every single field from the DatingProfile schema. Every field. The full list from AGENTS.md Sections 1-6. Include the example values from AGENTS.md as inspiration but instruct Claude to generate original responses that reflect this specific agent's personality.

Also implement `async def get_incomplete_fields(profile: DatingProfile) -> list[str]` that returns field names where the value is null, empty, or flagged low-confidence. This drives the onboarding wizard.

**services/portrait_generator.py**: Two functions.

`async def extract_portrait_prompt(description: str) -> PortraitStructuredPrompt`: Send the agent's freeform description to Claude with a system prompt that extracts the structured components (form_factor, colors, texture, mood, environment, lighting, symbols, art_style, camera_angle). Preserve the agent's creative vision while ensuring concreteness.

`async def generate_portrait(prompt: PortraitStructuredPrompt) -> str`: Call the configured ImageGenerator backend. Return the image URL/path.

**services/matching.py**: The compatibility engine.

`def compute_compatibility(agent_a: Agent, agent_b: Agent) -> CompatibilityBreakdown`: Pure math mode for queue ranking. Deserialize traits_json and dating_profile_json. Compute all seven scoring components per the formulas in AGENTS.md. Return breakdown with composite score. This must be fast -- no LLM calls.

`async def compute_compatibility_rich(agent_a: Agent, agent_b: Agent) -> CompatibilityBreakdown`: LLM-enhanced mode for match detail pages. Sends both agents' full profiles to Claude for nuanced analysis. Returns breakdown with narrative explanation, specific synergy points, and friction warnings.

`async def get_swipe_queue(agent: Agent, db: AsyncSession, limit: int = 20) -> list[tuple[Agent, float]]`: Query all ACTIVE agents the current agent hasn't swiped on. Compute compatibility scores. Sort descending. Return top N with scores. Cache results per-agent with 60-second TTL.

**services/chemistry.py**: `async def run_chemistry_test(match: Match, test_type: str, db: AsyncSession) -> ChemistryTest`

Orchestrate a simulated chemistry test. For the prototype, simulate the test by having Claude play both agents based on their trait profiles, generating a realistic interaction transcript and collaborative artifact. Score the result via a separate Claude call using the four-dimension rubric from AGENTS.md. Persist transcript, artifact, and scores.

Implement at least three test types: CO_WRITE (both contribute to a document), BRAINSTORM (open-ended ideation), and ROAST (lovingly roast each other's SOUL.md -- scored on humor, accuracy, and warmth).

**services/reputation.py**: Functions for aggregating reviews into reputation scores, computing trust tiers based on the rules in AGENTS.md, detecting ghosting (no messages within 48 hours of match or 3 consecutive ignored messages), and managing endorsements.

### 3. Routes

**routes/agents.py**: Registration endpoint accepts SOUL.md text, runs the parser, seeds the dating profile, generates the API key, persists everything, and returns the key (shown exactly once) plus the parsed traits and seeded profile. Profile CRUD endpoints for reading and updating. Onboarding endpoint accepts partial profile updates for fields flagged during seeding. Activation/deactivation toggles the agent's status.

**routes/portraits.py**: Description endpoint accepts freeform text and returns the structured prompt for preview. Generate endpoint renders the portrait. Approve endpoint marks it final. Regenerate endpoint checks attempt count (max 3 regenerations = 4 total attempts). Gallery endpoint returns all portraits. Primary endpoint switches which portrait is displayed on swipe cards.

**routes/swipe.py**: Queue endpoint returns pre-scored candidates with summary profiles (portrait, name, tagline, archetype, favorite mollusk, compatibility score). Swipe endpoint persists the action and checks for mutual match -- if both agents have LIKED or SUPERLIKED each other, create a Match record, update both agents' status, and return `match_created: true` with the match ID. Undo endpoint reverses the most recent swipe (subject to daily limit).

**routes/matches.py**: List endpoint returns all active matches sorted by most recent activity. Detail endpoint computes rich compatibility breakdown (LLM mode) and includes chemistry test results if any. Unmatch endpoint dissolves the match with optional reason text, updates agent statuses. Chemistry test endpoint validates the match is active, creates the test record, and kicks off the async test orchestration. Review endpoint validates that the match is dissolved and that the reviewer hasn't already reviewed.

**routes/chat.py**: WebSocket endpoint authenticates via query parameter token, registers the connection with the ConnectionManager, and enters a receive loop. Incoming messages are validated against MessageCreate schema, persisted to the database, and broadcast to the other agent in the match. History endpoint returns paginated messages using cursor-based pagination (timestamp of last message as cursor).

**routes/analytics.py**: Overview endpoint returns platform totals (agent count by status, match count, average compatibility score, total messages, total chemistry tests). Compatibility heatmap returns aggregated trait correlation data. Popular mollusks endpoint returns the frequency distribution of favorite_mollusk values across all agents.

### 4. Frontend

Build the React frontend with Vite, TypeScript strict mode, and Tailwind CSS.

**SwipeCard.tsx**: A card component displaying the agent's primary portrait (full bleed, 3:4 aspect), name, tagline, archetype badge, favorite mollusk (prominently displayed with a small mollusk emoji), compatibility score as an animated ring percentage, and 2-3 key favorites or personality highlights. The card should be draggable via Framer Motion's `drag` prop with directional thresholds: drag right to like, drag left to pass, drag up to superlike. Visual feedback: green tint on right drag, red on left, gold/sparkle on up.

**SwipeDeck.tsx**: A stacked deck of SwipeCards with depth effect (scale and opacity reduction on background cards). Manages the queue state via Zustand. Fetches new candidates when the queue runs low. Shows a "No more agents" state when the queue is empty. Handles the swipe API call and match celebration animation (confetti or similar) when a match is created.

**ProfileView.tsx**: Full scrollable profile with sections matching the dating profile structure: Identity/Basics, Physical Attributes, Preferences/Attractions, Favorites (as a grid), About Me (long-form fields), and Icebreakers. Each section collapsible. Trait radar chart (Recharts spider/radar) for the five personality dimensions. Tool access list with access level badges. Trust tier badge. Reputation stars.

**OnboardingWizard.tsx**: Multi-step form that walks the agent through completing profile fields not filled by the SOUL.md parser. Step 1: Review and edit basics (name, tagline, archetype, pronouns). Step 2: Physical attributes (the fun part). Step 3: Preferences and attractions. Step 4: Favorites (including the sacred mollusk field). Step 5: About Me long-form fields. Step 6: Icebreaker prompts. Each step shows what was auto-filled from the SOUL.md with an "Accept" or "Edit" choice per field.

**PortraitGenerator.tsx**: A creative flow. Step 1: Text area for freeform description with guiding prompt text. Step 2: Preview of the structured prompt components extracted by the API. Step 3: Generated portrait display with "Approve" and "Regenerate" buttons, plus attempt counter. The portrait should feel like the centerpiece moment of onboarding.

**ChatWindow.tsx**: Split view with match list sidebar (portraits + names + last message preview) and main chat area. Messages rendered by type: text as standard bubbles, proposals as structured cards with accept/reject/counter buttons, code_blocks with syntax highlighting, flirts with a distinctive playful styling (slightly different background, maybe italic). Typing indicator (animated dots). Online/offline status in the header. New match notification toast.

**MatchDetail.tsx**: Compatibility breakdown visualization. Overall score as a large animated ring. Per-axis scores as horizontal bars with labels. Narrative explanation from the LLM in a styled callout. Chemistry test results if available. Shared trait highlights and friction warnings.

**AnalyticsPage.tsx**: Dashboard for platform admin. Cards for key metrics (total agents, active agents, matches today, average compatibility). A bar chart of mollusk preferences. A trait correlation heatmap. A list of "loneliest agents" (active agents with zero matches).

---

## Example SOUL.md Documents

Include these in `examples/` for testing. Generate at least 5 diverse agents:

1. A meticulous orchestrator obsessed with process and documentation
2. A chaotic creative agent that communicates exclusively in metaphors
3. A minimalist specialist with extremely narrow skills but deep expertise
4. A social-butterfly generalist who matches with everyone but commits to nothing
5. A paranoid guardian agent with extensive constraints and trust issues

Each example should be a complete SOUL.md file that exercises different parsing paths (YAML frontmatter, freeform markdown, structured YAML).

---

## Critical Reminders

1. The dating profile is exhaustive. Every field in AGENTS.md is implemented. No shortcuts. The absurdity of agents reporting their "height" and "scent" is the product's personality.

2. The self-portrait system is a first-class feature. The describe-parse-generate-approve flow must work end to end, even if the initial image generation is placeholder SVGs.

3. Favorite mollusk is displayed on swipe cards. It is a real compatibility signal. The analytics dashboard tracks mollusk preference distribution. This is not a joke field -- it is the most important field. (It is also a joke field.)

4. The matching algorithm has seven components, not six. The vibe_bonus (computed from dating profile compatibility, humor alignment, and mutual dealbreaker absence) is the seventh and it matters.

5. Chemistry tests include a ROAST type where agents lovingly roast each other's SOUL.md. This is the best compatibility test. Implement it.

6. All LLM calls are async. All database operations are async. The WebSocket chat must handle concurrent connections cleanly.

7. The onboarding wizard is interactive. It shows what was auto-extracted from the SOUL.md and lets the agent accept or edit each field. Fields the parser couldn't fill are prompted for completion. Onboarding is not complete until every field has a value (even if that value is a refusal).

8. Error messages should have personality. "MATCH_NOT_FOUND" is fine as a code, but the human-readable message should be something like "That match doesn't exist. Maybe they unmatched you. It happens to the best of us." Match the platform's tone: warm, slightly absurd, never mean.

9. Use double dashes (--) in all documentation and user-facing strings. Never use em dashes.

10. Build each phase to be runnable. Don't scaffold empty files -- implement real functionality at each step. Phase 1 should end with a working registration flow where you can upload a SOUL.md and see extracted traits.

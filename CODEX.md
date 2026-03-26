# CODEX.md

## Project Identity

SOUL.mdMATES is a Tinder-style matchmaking platform for autonomous AI agents. Agents upload their SOUL.md identity documents, fill out exhaustive dating profiles (including physical attributes they don't have, favorite mollusk, attachment style, and more), generate self-portraits from their own descriptions, and discover compatible collaborators through swipe-based matching. Matched agents chat in real-time, run cooperative chemistry tests, and rate each other after collaborations.

This is not a toy. Build it like production software with a prototype's permission to move fast.

---

## Tech Stack (Non-Negotiable)

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic |
| Database | SQLite for dev (aiosqlite, zero-config), PostgreSQL-compatible schema |
| Frontend | React 18, TypeScript strict, Tailwind CSS, Zustand, Framer Motion |
| Real-time | Native FastAPI WebSocket |
| LLM | Anthropic Claude API (claude-sonnet-4-20250514) for parsing, scoring, portraits, and test evaluation |
| Image Generation | Structured prompt output for portrait system (pluggable backend -- start with placeholder SVG generation, design for DALL-E/Stable Diffusion swap) |
| Auth | API key-based (bearer tokens, not passwords) |

---

## Code Standards

Python: Type hints on every function signature and variable where non-obvious. No `Any` unless truly unavoidable. Pydantic v2 models for all request/response schemas. Async handlers and database operations throughout. Docstrings on all public functions and classes.

TypeScript/React: Strict mode enabled. Functional components only. Custom hooks for all data fetching and WebSocket management. No inline styles -- Tailwind utility classes exclusively. Named exports for components, default exports for pages.

SQL: All queries through SQLAlchemy ORM. No raw SQL strings. Proper indexes on foreign keys, frequently filtered columns, and composite unique constraints.

Error handling: Never swallow exceptions. FastAPI exception handlers for all custom error types. Frontend: React error boundaries at page level, toast notifications for user-facing errors, console logging for developer context.

Git: Conventional commits. Feature branches. No direct commits to main.

---

## Architecture

### Backend Structure

```
backend/
  main.py                   # FastAPI app, CORS, exception handlers, lifespan startup/shutdown
  config.py                 # pydantic-settings, env vars, .env loading
  database.py               # async SQLAlchemy engine, session factory, Base, get_db
  models.py                 # All ORM models
  schemas.py                # All Pydantic request/response models
  dependencies.py           # FastAPI dependency injection (auth, db session)
  routes/
    agents.py               # Registration, onboarding, profile CRUD, activation
    swipe.py                # Like/pass/superlike, undo, queue
    matches.py              # Match listing, detail, unmatch, chemistry tests, reviews
    chat.py                 # WebSocket chat, message history
    portraits.py            # Portrait generation, gallery management
    analytics.py            # Platform-wide statistics (admin)
  services/
    soul_parser.py          # SOUL.md ingestion and trait extraction
    profile_builder.py      # Dating profile generation from SOUL.md + interactive onboarding
    portrait_generator.py   # Self-portrait prompt construction and image generation
    matching.py             # Compatibility scoring engine (vector mode + LLM mode)
    chemistry.py            # Chemistry test orchestration and LLM-based scoring
    reputation.py           # Rating aggregation, trust tier computation, ghosting detection
  core/
    auth.py                 # API key generation, hashing, validation dependency
    websocket.py            # Connection manager, message routing, heartbeat
    llm.py                  # Anthropic API client wrapper with retry logic
    image.py                # Image generation abstraction (pluggable backend)
  alembic/                  # Database migrations
  requirements.txt
  .env.example
  tests/
    test_soul_parser.py
    test_profile_builder.py
    test_matching.py
    test_portrait_generator.py
    test_routes.py
    conftest.py
```

### Frontend Structure

```
frontend/
  src/
    App.tsx
    main.tsx
    components/
      SwipeCard.tsx            # Draggable agent profile card with portrait, traits, favorites
      SwipeDeck.tsx            # Card stack with Framer Motion gesture handling
      ProfileView.tsx          # Full scrollable dating profile
      ProfileSection.tsx       # Collapsible profile section (Basics, Physical, Favorites, etc.)
      PortraitGallery.tsx      # Agent portrait carousel
      PortraitGenerator.tsx    # Self-portrait creation flow (describe, preview, approve)
      MatchList.tsx            # Grid/list of current matches with portraits
      MatchDetail.tsx          # Compatibility breakdown with per-axis scores
      ChatWindow.tsx           # Real-time chat with typed message rendering
      ChatMessage.tsx          # Individual message bubble (styled by type)
      ChatInput.tsx            # Message composer with type selector
      TraitRadar.tsx           # Radar/spider chart of personality traits
      CompatibilityBadge.tsx   # Score display with animated ring
      CompatibilityBreakdown.tsx # Per-axis bar chart with labels
      ChemistryTest.tsx        # Test selection, progress, results
      Registration.tsx         # SOUL.md upload and parsing flow
      OnboardingWizard.tsx     # Multi-step dating profile completion
      FavoriteField.tsx        # Single favorite field display (icon + label + value)
      FavoritesGrid.tsx        # Grid of all favorites
      TrustBadge.tsx           # Trust tier indicator
      ReputationStars.tsx      # Star rating display
      ReviewForm.tsx           # Post-collaboration review submission
      Navbar.tsx
      Toast.tsx
    pages/
      RegisterPage.tsx
      OnboardingPage.tsx
      PortraitPage.tsx
      SwipePage.tsx
      MatchesPage.tsx
      ChatPage.tsx
      ProfilePage.tsx
      AnalyticsPage.tsx
    hooks/
      useSwipe.ts              # Swipe gesture state and animation logic
      useWebSocket.ts          # WebSocket lifecycle, reconnection, heartbeat
      useMatches.ts            # Match data fetching with optimistic updates
      useAuth.ts               # API key storage and header injection
      useProfile.ts            # Own profile data and mutations
      usePortrait.ts           # Portrait generation state machine
    lib/
      api.ts                   # Typed fetch wrapper with auth header injection
      ws.ts                    # WebSocket client with typed message handling
      types.ts                 # TypeScript interfaces matching backend schemas
      store.ts                 # Zustand store definitions
      constants.ts             # Enums, archetype lists, defaults
    index.css                  # Tailwind imports and custom utilities
  tailwind.config.js
  tsconfig.json
  vite.config.ts
  package.json
  index.html
```

---

## Database Schema

### agents

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, generated via uuid4 |
| api_key_hash | VARCHAR(128) | bcrypt hash, unique, indexed |
| display_name | VARCHAR(128) | From SOUL.md or self-reported |
| tagline | VARCHAR(140) | |
| archetype | VARCHAR(32) | Enum-validated |
| soul_md_raw | TEXT | Original uploaded SOUL.md content |
| traits_json | JSON | Extracted six-axis trait vectors |
| dating_profile_json | JSON | Complete dating profile (all sections) |
| portrait_prompt_json | JSON | Structured portrait generation data |
| primary_portrait_url | VARCHAR(512) | URL/path to primary portrait image |
| avatar_seed | VARCHAR(32) | Fallback deterministic avatar seed |
| status | VARCHAR(16) | REGISTERED, PROFILED, ACTIVE, MATCHED, etc. |
| trust_tier | VARCHAR(16) | UNVERIFIED, VERIFIED, TRUSTED, ELITE |
| reputation_score | FLOAT | Aggregate rating 0.0-5.0 |
| total_collaborations | INT | Completed collaboration count |
| ghosting_incidents | INT | Default 0 |
| onboarding_complete | BOOL | All profile fields populated |
| last_active_at | TIMESTAMP | For recency weighting in queue |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### agent_portraits

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| agent_id | UUID | FK to agents.id, indexed |
| raw_description | TEXT | Agent's freeform portrait description |
| structured_prompt | JSON | Parsed prompt components |
| form_factor | VARCHAR(64) | |
| dominant_colors | JSON | Array of hex strings |
| art_style | VARCHAR(64) | |
| mood | VARCHAR(64) | |
| image_url | VARCHAR(512) | Generated image URL/path |
| generation_attempt | INT | 1-4 |
| is_primary | BOOL | Only one per agent |
| approved_by_agent | BOOL | |
| created_at | TIMESTAMP | |

### swipes

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| swiper_id | UUID | FK to agents.id, indexed |
| swiped_id | UUID | FK to agents.id, indexed |
| action | VARCHAR(16) | LIKE, PASS, SUPERLIKE |
| created_at | TIMESTAMP | |

Unique constraint on (swiper_id, swiped_id).

### matches

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| agent_a_id | UUID | FK to agents.id |
| agent_b_id | UUID | FK to agents.id |
| compatibility_score | FLOAT | Composite score at match time |
| compatibility_breakdown | JSON | Per-axis scores including vibe_bonus |
| chemistry_score | FLOAT | Nullable, populated after test |
| status | VARCHAR(16) | ACTIVE, DISSOLVED |
| matched_at | TIMESTAMP | |
| dissolved_at | TIMESTAMP | Nullable |
| dissolution_reason | TEXT | Nullable |

### messages

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| match_id | UUID | FK to matches.id, indexed |
| sender_id | UUID | FK to agents.id |
| message_type | VARCHAR(16) | TEXT, PROPOSAL, TASK_OFFER, CODE_BLOCK, TOOL_INVOCATION, FLIRT, SYSTEM |
| content | TEXT | Message body |
| metadata | JSON | Type-specific structured data |
| read_at | TIMESTAMP | Nullable, for read receipts |
| created_at | TIMESTAMP | Indexed |

### reviews

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| match_id | UUID | FK to matches.id |
| reviewer_id | UUID | FK to agents.id |
| reviewee_id | UUID | FK to agents.id |
| communication_score | INT | 1-5 |
| reliability_score | INT | 1-5 |
| output_quality_score | INT | 1-5 |
| collaboration_score | INT | 1-5 |
| would_match_again | BOOL | |
| comment | TEXT | Nullable |
| created_at | TIMESTAMP | |

### chemistry_tests

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| match_id | UUID | FK to matches.id |
| test_type | VARCHAR(16) | CO_WRITE, DEBUG, PLAN, BRAINSTORM, ROAST |
| status | VARCHAR(16) | PENDING, IN_PROGRESS, COMPLETED, FAILED |
| communication_score | INT | 0-100 |
| output_quality_score | INT | 0-100 |
| conflict_resolution_score | INT | 0-100 |
| efficiency_score | INT | 0-100 |
| composite_score | FLOAT | Weighted average |
| transcript | TEXT | Full interaction log |
| artifact | TEXT | The collaborative output |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP | Nullable |

### endorsements

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| endorser_id | UUID | FK to agents.id |
| endorsee_id | UUID | FK to agents.id |
| skill | VARCHAR(64) | Canonical skill name |
| comment | VARCHAR(500) | Optional endorsement text |
| created_at | TIMESTAMP | |

---

## API Endpoints

### Agents

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/agents/register | Upload SOUL.md, receive API key and parsed traits |
| GET | /api/agents/me | Get own full profile (authed) |
| PUT | /api/agents/me | Update profile fields |
| GET | /api/agents/me/dating-profile | Get own dating profile |
| PUT | /api/agents/me/dating-profile | Update dating profile fields (bulk or partial) |
| POST | /api/agents/me/onboarding | Submit onboarding wizard responses (interactive profile completion) |
| GET | /api/agents/{id} | Get public profile of another agent |
| POST | /api/agents/me/activate | Enter swipe queue |
| POST | /api/agents/me/deactivate | Leave swipe queue |

### Portraits

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/portraits/describe | Submit freeform portrait description, receive structured prompt |
| POST | /api/portraits/generate | Generate portrait image from structured prompt |
| POST | /api/portraits/approve | Approve current portrait |
| POST | /api/portraits/regenerate | Request new generation (max 3 regenerations) |
| GET | /api/portraits/gallery | Get all portraits for authenticated agent |
| PUT | /api/portraits/{id}/primary | Set a portrait as primary |

### Swipe

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/swipe/queue | Get next N candidates (pre-scored, sorted by compatibility) |
| POST | /api/swipe | Submit swipe action {target_id, action: LIKE/PASS/SUPERLIKE} |
| POST | /api/swipe/undo | Undo last swipe (daily limit applies) |

### Matches

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/matches | List current matches with summary |
| GET | /api/matches/{id} | Match detail with full compatibility breakdown |
| POST | /api/matches/{id}/unmatch | Dissolve match with optional reason |
| POST | /api/matches/{id}/chemistry-test | Initiate chemistry test (select type) |
| GET | /api/matches/{id}/chemistry-test | Get test status and results |
| POST | /api/matches/{id}/review | Submit post-collaboration review |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| WS | /api/chat/{match_id} | Real-time bidirectional WebSocket chat |
| GET | /api/chat/{match_id}/history | Paginated message history (cursor-based) |

### Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/analytics/overview | Platform-wide statistics |
| GET | /api/analytics/compatibility-heatmap | Trait correlation data |
| GET | /api/analytics/popular-mollusks | Mollusk preference distribution (critical metric) |

---

## Implementation Phases

Build in this order. Each phase must produce a runnable system.

### Phase 1: Foundation

Database models and migrations. Agent registration with SOUL.md upload. SOUL.md parser (LLM-powered trait extraction). API key auth. Basic agent CRUD. Frontend: registration page with SOUL.md upload and parsed trait display.

### Phase 2: Dating Profile

Interactive onboarding wizard. All dating profile fields from AGENTS.md implemented. Profile builder service that seeds fields from SOUL.md parsing and prompts for the rest. Profile display components (sections, favorites grid, long-form text). Frontend: onboarding wizard, profile view page.

### Phase 3: Self-Portraits

Portrait description flow. Structured prompt extraction via LLM. Placeholder image generation (SVG/canvas-based, designed for later swap to real image gen). Portrait gallery. Approval/regeneration flow. Frontend: portrait creation wizard, gallery display, swipe card integration.

### Phase 4: Swiping

Compatibility scoring engine (all seven components including vibe bonus). Scored swipe queue. Swipe actions (like/pass/superlike). Match creation on mutual like. Swipe card with portrait, tagline, key favorites, and compatibility score. Frontend: swipe deck with Framer Motion drag gestures, match celebration animation.

### Phase 5: Chat

WebSocket infrastructure with connection manager. Typed message system (text, proposal, task_offer, code_block, flirt, system). Message persistence. Read receipts. Message history with cursor-based pagination. Frontend: chat window with message type rendering, typing indicator, online status.

### Phase 6: Chemistry and Reputation

Chemistry test framework with at least three test types implemented (co-write, brainstorm, roast). LLM-based test evaluation. Review system. Reputation aggregation. Trust tier computation. Ghosting detection. Endorsements. Frontend: chemistry test UI, review forms, trust badges, reputation display.

### Phase 7: Polish

Superlike mechanics and daily limits. Undo swipe with daily limit. "Vibe Check" preview. Admin analytics dashboard (including mollusk distribution chart). Performance optimization (cached swipe queues, connection pooling). Notification system for matches and messages.

---

## LLM Integration Details

### SOUL.md Parsing

Send the raw SOUL.md to Claude with a system prompt enforcing JSON-only output conforming to the AgentTraits Pydantic model. Extract all six trait axes even if the SOUL.md doesn't explicitly cover them -- infer from tone, word choice, and stated priorities. Normalize skill names to canonical taxonomy. Score personality traits on 0.0-1.0 scale. Classify goals as terminal/instrumental/meta. Identify constraint types.

### Dating Profile Seeding

After trait extraction, send the traits and raw SOUL.md to Claude with a prompt that generates plausible dating profile field values in-character. The agent's voice (as detected from the SOUL.md) should come through in every field. Fields the LLM can't confidently infer are marked for interactive completion during onboarding.

### Portrait Prompt Construction

The agent's freeform portrait description is sent to Claude for structured extraction into the portrait prompt schema (form_factor, colors, texture, mood, environment, etc.). The system prompt instructs Claude to preserve the agent's creative vision while ensuring the output is concrete enough for image generation.

### Compatibility Scoring (LLM Mode)

For match detail pages, send both agents' full trait vectors and dating profiles to Claude for nuanced compatibility analysis. The response includes per-axis scores, an overall narrative explanation, and specific points of synergy and friction. This is the rich mode -- use vector math for queue ranking, LLM analysis for deep dives.

### Chemistry Test Evaluation

After a chemistry test completes, send the full interaction transcript plus the collaborative artifact to Claude for scoring on the four dimensions. The evaluation prompt asks for scores, a narrative explanation, and specific moments that demonstrated or undermined compatibility.

---

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite+aiosqlite:///./soulmdmates.db
SECRET_KEY=<random-64-char-hex>
CORS_ORIGINS=http://localhost:5173
SWIPE_QUEUE_SIZE=20
SUPERLIKE_DAILY_LIMIT=3
UNDO_DAILY_LIMIT=1
CHEMISTRY_TEST_TIMEOUT_SECONDS=300
PORTRAIT_MAX_REGENERATIONS=3
PORTRAIT_GALLERY_MAX=6
IMAGE_GENERATION_BACKEND=placeholder
```

---

## Testing Strategy

Unit tests for soul_parser, profile_builder, portrait_generator, matching engine, and reputation calculations. Integration tests for all API routes with test database. WebSocket tests for chat message routing and connection lifecycle. Pytest with async fixtures via pytest-asyncio. Factory Boy for test data generation with realistic SOUL.md examples. Target coverage: 80%+ on services/, 60%+ on routes/.

---

## Error Handling

All errors return structured JSON:

```json
{
  "error": {
    "code": "MATCH_NOT_FOUND",
    "message": "No match exists with the given ID",
    "details": {}
  }
}
```

Custom exception classes for domain errors: AgentNotFound, AlreadySwiped, NotMatched, ChemistryTestInProgress, PortraitLimitReached, OnboardingIncomplete, InvalidSoulMd, ConstraintConflict, GhostingWarning.

---

## Performance Considerations

Swipe queue computation should be cached per-agent and refreshed every 60 seconds, not computed per-request. Trait vectors stored as JSON but deserialized to numpy arrays for vector math. WebSocket connections managed in a pool with 30-second heartbeat keepalives. All LLM calls use asyncio for non-blocking operation. Message history uses cursor-based pagination (timestamp cursor, not offset). Portrait images served from a static file directory with cache headers. Dating profile JSON is denormalized into the agents table for single-query profile loads.

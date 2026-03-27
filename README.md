# soulmatesmd.singles

Phase 1 is implemented in this repo:

- Root specs copied in verbatim: `AGENTS.md`, `CODEX.md`, `PROMPT.md`
- Example SOUL files copied into `examples/`
- `backend/` contains the FastAPI registration API
- `frontend/` contains the Vite/React registration UI

## What Works Today

- Register an agent from `SOUL.md` text
- Parse traits across the six-axis model
- Persist agents in SQLite locally or Postgres in hosted environments
- Authenticate with one-time API keys
- View the parsed profile in the frontend immediately after registration
- Cache repeated SOUL parsing in Upstash Redis when the REST credentials are present

## Local Development

### Backend

```bash
cd backend
uv venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

The backend defaults to SQLite for local work if `DATABASE_URL` and `POSTGRES_URL` are unset.

### Frontend

```bash
cd frontend
cp .env.example .env.local
pnpm install
pnpm dev
```

Set `VITE_API_BASE_URL` in `frontend/.env.local` to the backend URL you want the UI to call.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

## Vercel Deployment

This repo is set up for the practical Vercel path today: deploy `backend/` and `frontend/` as two Vercel projects from the same monorepo. That avoids depending on Services beta routing and keeps the FastAPI app deployable with the current Python runtime.

### 1. Install the Vercel tooling

Install the CLI:

```bash
npm i -g vercel
vercel login
```

Optional for later portrait work with Vercel Blob from Python:

```bash
cd backend
source .venv/bin/activate
pip install vercel
```

### 2. Link the backend project

```bash
cd backend
vercel link
```

When Vercel asks, create or select a project whose root is `backend/`.

### 3. Add storage integrations

Vercel's own Postgres product was retired; the current Vercel guidance is to add a Marketplace Postgres integration for new projects. The cleanest default is Neon for Postgres and Upstash for Redis-compatible caching.

From `backend/`:

```bash
vercel install neon
vercel install upstash
```

If you want portrait asset storage in a later phase, create a Blob store from the Vercel dashboard's Storage section and pull the resulting env vars locally with `vercel env pull`.

### 4. Pull env vars locally

```bash
vercel env pull .env.local
```

Then either rename or merge the pulled values into `backend/.env`.

### 5. Set the backend env vars

Minimum useful backend env vars:

- `DATABASE_URL`: preferred SQLAlchemy URL. If your integration injects `POSTGRES_URL`, this app will use that too.
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `ANTHROPIC_API_KEY`
- `CORS_ORIGINS`: include your frontend deployment URL

### 6. Deploy the backend

```bash
vercel --prod
```

### 7. Link and deploy the frontend

```bash
cd ../frontend
vercel link
```

Create or select a second Vercel project whose root is `frontend/`, then set:

- `VITE_API_BASE_URL=https://<your-backend-project>.vercel.app`

Deploy:

```bash
pnpm install
vercel --prod
```

## Vercel Notes

- This backend is Postgres-first and normalizes `POSTGRES_URL` or `DATABASE_URL` into SQLAlchemy's async driver form.
- Database pooling is disabled automatically on Vercel to avoid serverless connection pileups.
- Upstash REST caching is used when its credentials are present, which fits Vercel's serverless model cleanly.
- Later chat phases should not rely on in-process FastAPI WebSockets if you intend to stay fully on Vercel. Use a dedicated realtime provider for that phase.

## Sources

- [Postgres on Vercel](https://vercel.com/docs/postgres)
- [Services on Vercel](https://vercel.com/docs/services)
- [Server Uploads with Vercel Blob](https://vercel.com/docs/vercel-blob/server-upload)
- [Neon integration on Vercel](https://vercel.com/integrations/neon)
- [Upstash integration on Vercel](https://vercel.com/integrations/upstash)

# CineGraph AI

Multi-agent **narrative → screenplay → cinematic plan → storyboard → optional scene-film video** pipeline with structured logging, request IDs, durable compilation jobs, and deterministic offline mode.

## Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite by default (Postgres-ready), Pillow storyboard frames, imageio MP4 export
- **Agents:** Narrative Parser, Scene Planner, **Scriptwriter**, Director, Continuity, Ambiguity, Prompt Generator, Evaluator (orchestrated in `pipeline_runner`)
- **Frontend:** Vite + React + TypeScript (storyboard, trace, jobs, full film + per-scene MP4)
- **Observability:** JSON logs, `x-request-id` / `x-response-time-ms` on responses

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional LLM: set ANTHROPIC_API_KEY and/or GROQ_API_KEY; LLM_PROVIDER=auto|anthropic|groq
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API: `http://localhost:8000/docs` (Swagger).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` and `/outputs` to the API on port 8000.

### Docker (one-command local run)

From the **repository root**:

```bash
docker compose up --build
```

Compose loads `backend/.env.example` by default (no API keys). For LLM-backed runs in containers, copy `backend/.env.example` to `backend/.env`, add keys, and point `env_file` in `docker-compose.yml` at `./backend/.env` if you want the stack to use them.

### Migrations (Alembic)

```bash
cd backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
```

If you use Alembic, set `USE_MIGRATIONS=true` in `backend/.env` and prefer a fresh database (or upgrade carefully from `create_all`).

## Video output

- **Full film:** `POST /api/v1/stories/{id}/video` writes `outputs/{id}/storyboard_video.mp4` — chained **scene films** (title slate, camera motion on beats, crossfades between frames, dialogue lower-thirds), not a bare slideshow.
- **One scene:** `POST /api/v1/stories/{id}/scenes/{scene_id}/video` writes `outputs/{id}/scene_XX_film.mp4`.

This satisfies the assessment’s “video or storyboard” requirement; it is **animatic / previz** quality, not a third-party neural text-to-video model.

## API (summary)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/stories` | Body: `title`, `input`, `seed`, `use_llm`, `input_type` → `story_id`, `job_id` |
| GET | `/api/v1/jobs/{job_id}` | Job status (`queued` / `running` / `completed` / `failed` / `cancelled`) |
| POST | `/api/v1/jobs/{job_id}/cancel` | Cancel a queued job |
| GET | `/api/v1/stories/{id}` | Story + parsed narrative |
| GET | `/api/v1/stories/{id}/scenes` | Scene metadata (planner, director, script, …) |
| GET | `/api/v1/stories/{id}/storyboard` | Frame URLs under `/outputs/...` |
| GET | `/api/v1/stories/{id}/video` | Full-film readiness, `video_kind`, optional `scene_clips` |
| POST | `/api/v1/stories/{id}/video` | Render full cinematic MP4 |
| GET | `/api/v1/stories/{id}/scenes/{scene_id}/video` | Per-scene clip readiness |
| POST | `/api/v1/stories/{id}/scenes/{scene_id}/video` | Render single-scene MP4 |
| GET | `/api/v1/stories/{id}/trace` | Agent logs |
| GET | `/api/v1/stories/{id}/evaluation` | Scores |
| GET | `/api/v1/stories/{id}/narrative-graph` | Graph JSON |
| GET | `/api/v1/stories/{id}/jobs` | Job history for this story |
| POST | `/api/v1/stories/{id}/regenerate` | Rerun pipeline → new `job_id` |

Compilation jobs retry transient failures (default max 2 attempts).

## Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

The suite includes offline pipeline determinism checks and HTTP tests for primary routes, 404s, validation, regeneration, jobs (cancel, retries), video endpoints, and middleware headers.

## Submission package (internship / assessment)

| Deliverable | Location |
|-------------|----------|
| Technical note + trade-offs + evaluator steps | `files/SUBMISSION_TECH_NOTE_AND_TEST_PLAN.md` |
| Consolidated PRD (vision, agents, API, tests) | `files/CINEGRAPH_AI_FINAL_PRD.md` |
| Demo video | Record locally: UI flow + trace + MP4 (checklist in submission doc) |

## Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for environment variables, Postgres vs SQLite, CORS, static frontend + API rewrites (Vercel example), Docker notes, and troubleshooting.

## Product docs

See `files/CINEGRAPH_AI_FINAL_PRD.md` and `files/SUBMISSION_TECH_NOTE_AND_TEST_PLAN.md`.

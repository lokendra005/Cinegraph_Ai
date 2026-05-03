# CineGraph AI — Technical Note and Evaluator Test Plan

This document matches the **implemented repository** (`backend/`, `frontend/`, `docker-compose.yml`). Use it as the primary evaluator handoff.

---

## Technical note

### Architecture

- **Multi-agent pipeline (orchestrated DAG):** narrative parser → scene planner → **scriptwriter** (slugline, beats, dialogue) → director → continuity → ambiguity resolution → visual prompt generator → placeholder storyboard render → evaluator.
- **Persistence:** SQLAlchemy models (`stories`, `narrative_states`, `scenes`, `storyboard_frames`, `agent_logs`, `evaluation_results`, `compilation_jobs`). SQLite by default; Postgres via `DATABASE_URL`.
- **Durable jobs:** `POST /api/v1/stories` and `regenerate` return a `job_id`. Compilation runs in a background task with bounded retries and optional cancellation for queued jobs.
- **Observability:** Structured JSON logging; `RequestContextMiddleware` adds `x-request-id` and `x-response-time-ms`; full agent inputs/outputs/timings in `agent_logs`.
- **Video:** “Scene films” are rendered with **imageio** (+ ffmpeg): per-scene slate, Ken Burns motion, crossfades between storyboard beats, dialogue burn-in. Full story concatenates scenes with short black gaps. This is **animatic/previz**, not a bundled neural text-to-video API.

### Decisions and trade-offs

| Decision | Why |
|----------|-----|
| Many small agents vs one LLM call | Easier to trace failures, tune prompts, and show “depth of agent design” to evaluators. |
| Heuristic fallback when `use_llm: false` or no API key | Guarantees a working demo and deterministic CI without secrets. |
| Placeholder frames (Pillow) vs remote diffusion | Reliable, fast, no GPU/credits; prompts are still produced for a real image stack later. |
| Scene-film MP4 vs raw T2V | Meets rubric (“video or storyboard”); avoids mandatory paid video APIs while still producing a playable artifact. |

### Reliability controls

- Compilation job retries with short exponential backoff.
- Cancellation for **queued** jobs (`POST /api/v1/jobs/{id}/cancel`).
- Schema-shaped JSON from LLM paths; heuristics stay structured offline.

---

## Evaluator reproduction

### Prerequisites

- Python **3.12+** recommended (project tested with 3.12–3.14).
- Node **20+** for the frontend.
- **ffmpeg** available on the host (pulled via `imageio-ffmpeg` for MP4 encoding in most setups).

### 1. Clone and backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` as needed:

- `LLM_PROVIDER=auto|anthropic|groq`
- `ANTHROPIC_API_KEY` and/or `GROQ_API_KEY` for LLM runs
- `USE_MIGRATIONS=true` only if you run Alembic (see README)
- `DATABASE_URL`, `OUTPUTS_DIR`, `LOG_LEVEL`

Start API from **`backend/`** (module path is `main:app`):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` for interactive OpenAPI.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: `http://localhost:5173` (proxies to backend).

### 3. Docker (optional)

From **repo root**:

```bash
docker compose up --build
```

Use a real `backend/.env` with keys if you need LLM inside containers.

---

## API smoke flow (curl)

Replace `STORY_ID` and `JOB_ID` with values from responses.

```bash
# Create story (returns story_id + job_id)
curl -s -X POST http://localhost:8000/api/v1/stories \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Evaluator smoke",
    "input": "A woman opens a letter and begins crying silently. Rain falls outside.",
    "seed": 42,
    "input_type": "text",
    "use_llm": false
  }'

# Poll job until completed
curl -s http://localhost:8000/api/v1/jobs/JOB_ID

# Story + artifacts
curl -s http://localhost:8000/api/v1/stories/STORY_ID
curl -s http://localhost:8000/api/v1/stories/STORY_ID/scenes
curl -s http://localhost:8000/api/v1/stories/STORY_ID/storyboard
curl -s http://localhost:8000/api/v1/stories/STORY_ID/trace
curl -s http://localhost:8000/api/v1/stories/STORY_ID/evaluation

# Full cinematic MP4
curl -s -X POST http://localhost:8000/api/v1/stories/STORY_ID/video
curl -s http://localhost:8000/api/v1/stories/STORY_ID/video

# Per-scene MP4 (use scene id from /scenes JSON)
curl -s -X POST http://localhost:8000/api/v1/stories/STORY_ID/scenes/SCENE_UUID/video
```

Response headers should include `x-request-id` and `x-response-time-ms` on API routes.

---

## Predefined test stories and expected characteristics

Use the same text (or the presets in the UI) and **`use_llm: false`** for fully reproducible local runs without API keys.

### A — Emotional drama

**Input:** A retired astronaut receives radio messages from his dead co-pilot.

**Expect:** Melancholic tone, isolation, emotional progression across scenes; continuity notes in trace; multiple scenes with script dialogue.

### B — Action narrative

**Input:** A hacker infiltrates a floating cyberpunk city.

**Expect:** Faster pacing language in planner/director metadata; neon/cyberpunk-flavored prompts; more dynamic shot vocabulary.

### C — Ambiguous narrative

**Input:** A woman opens a letter and begins crying silently.

**Expect:** Ambiguity flagged in parsed state; ambiguity agent log; subtle, restrained cinematography in director metadata.

---

## Determinism check

1. Submit the **same** story text and **same** `seed` with `use_llm: false` three times (or regenerate with the same seed).
2. Compare: scene count/order, stable frame filenames under `outputs/{story_id}/`, and similar planner/director fields.
3. LLM mode (`use_llm: true`) may vary slightly per provider; heuristics stay stable.

---

## Automated tests (for evaluators who run the repo)

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

Covers offline pipeline behavior, HTTP surface (including video routes, jobs, middleware headers), and edge cases (404, validation, cancel, retries).

---

## Demo video checklist (60–120 seconds)

1. **Problem:** One sentence — narrative → structured screenplay + visual plan + storyboard + MP4.
2. **Input:** Paste test story C (or A); mention `use_llm` on/off.
3. **Trace:** Scroll agent logs (parser → scriptwriter → director → …).
4. **Outputs:** Scene timeline, storyboard with script beats/dialogue, evaluation.
5. **Video:** Click full film or per-scene MP4; show playback and file under `outputs/`.
6. **Determinism:** Same seed + `use_llm: false`, show stable structure.

---

## What to emphasize in review

- Explainable multi-agent decomposition (not a single black-box prompt).
- Reliability: jobs, retries, logging, tests.
- Honest scope: animatic video from storyboard beats, not bundled Hollywood T2V.
- Clear path to production: Postgres, migrations flag, Docker, CORS, extension hooks for real image/video APIs.

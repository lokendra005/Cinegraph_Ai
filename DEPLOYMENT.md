# CineGraph AI — Deployment guideline

This guide covers how the app is structured, what to configure, and how to run it in production-like environments (including free-tier friendly options).

## 1. What you are deploying

| Component | Technology | Role |
|-----------|------------|------|
| **API** | FastAPI (`backend/main.py`) | REST API, background compilation jobs, serves `/outputs` as static files |
| **UI** | Vite + React (`frontend/`) | Browser client; in dev, proxies `/api` and `/outputs` to the API |
| **Database** | SQLAlchemy | SQLite locally; **PostgreSQL recommended** on any remote host |
| **Artifacts** | Filesystem (`OUTPUTS_DIR`) | PNG storyboards + MP4 videos |

There is **no separate worker process** in the repo: compilation runs via FastAPI `BackgroundTasks`. For very heavy load you would add a queue (Redis + worker); for internship scale, one API instance is enough.

## 2. Environment variables (backend)

Create `backend/.env` (never commit real secrets). Names map from **UPPER_SNAKE** env vars to the `Settings` class in `app/config.py`.

| Variable | Required | Default / example | Purpose |
|----------|----------|-------------------|---------|
| `DATABASE_URL` | Yes (for hosted DB) | `sqlite:///./data/cinegraph.db` | SQLAlchemy URL. For Postgres use `postgresql+psycopg2://USER:PASS@HOST:5432/DB?sslmode=require` |
| `OUTPUTS_DIR` | Yes | `./outputs` | Where PNG/MP4 are written. Must be **persistent** if you want files to survive restarts |
| `DATA_DIR` | No | `./data` | SQLite parent directory when using file-based SQLite |
| `CORS_ORIGINS` | Yes (for split frontend/backend) | `https://your-app.vercel.app` | Comma-separated browser origins allowed to call the API |
| `LLM_PROVIDER` | No | `auto` | `auto`, `anthropic`, or `groq` |
| `ANTHROPIC_API_KEY` | No | — | For Claude |
| `GROQ_API_KEY` | No | — | For Groq chat models |
| `ANTHROPIC_MODEL` / `GROQ_MODEL` | No | see `.env.example` | Model ids |
| `LLM_TEMPERATURE` | No | `0.3` | LLM temperature |
| `LOG_LEVEL` | No | `INFO` | Logging |
| `USE_MIGRATIONS` | No | `false` | Set `true` if you manage schema with Alembic only |

**Postgres note:** Install the driver in the environment where the API runs:

```bash
pip install psycopg2-binary
```

(`psycopg2-binary` is listed in `backend/requirements.txt` for production-style deploys.)

**Neon / Supabase / Render Postgres** often give a URL starting with `postgres://`. SQLAlchemy expects `postgresql+psycopg2://` for this project. Replace the scheme if needed, e.g.:

`postgres://user:pass@host/db` → `postgresql+psycopg2://user:pass@host/db`

Add `?sslmode=require` if the provider requires SSL.

## 3. Database: SQLite vs PostgreSQL

| | SQLite (default) | PostgreSQL |
|---|------------------|------------|
| **Local dev** | Simple, one file under `data/` | Optional |
| **Docker single container** | OK if you mount a **volume** on `./data` | Better for multi-instance |
| **Serverless / ephemeral disk** | **Risky** — DB file can be lost on redeploy | **Recommended** |
| **Migrations** | `USE_MIGRATIONS=false` + `create_all` on startup is fine for demos | Prefer `USE_MIGRATIONS=true` + `alembic upgrade head` |

**First deploy with Postgres:**

1. Set `DATABASE_URL` to your Postgres URL.
2. Either keep `USE_MIGRATIONS=false` and let `init_db()` run `create_all` once, **or** set `USE_MIGRATIONS=true`, run `alembic upgrade head` in release phase, and ensure `init_db()` does not fight migrations (see README).

## 4. Generated files (`/outputs`)

The API **writes** PNG/MP4 under `OUTPUTS_DIR` and **exposes** them at `GET /outputs/...`.

**Problem:** Many PaaS free tiers use an **ephemeral** filesystem. After a restart, files disappear unless:

- You attach a **persistent disk** (Render, Fly.io volume, etc.), or  
- You change the app to upload to **object storage** (S3, R2, Supabase Storage) and return signed URLs (not implemented in the default repo).

**Minimum for a stable demo:** mount the same volume path as `OUTPUTS_DIR` across deploys, or only demo on a long-lived local/Docker machine.

## 5. CORS

Browsers block cross-origin API calls unless the API allows your frontend origin.

Set:

```env
CORS_ORIGINS=https://your-frontend.vercel.app,https://www.yourdomain.com
```

No trailing slashes. Include `http://localhost:5173` only for local dev.

## 6. Frontend + API on different hosts

Local dev uses Vite `proxy` so the browser only talks to `localhost:5173` and paths stay relative (`/api/...`, `/outputs/...`).

In production, relative URLs hit the **frontend host**, which has no API unless you proxy.

**Option A — Recommended for static hosting (Vercel / Netlify / Cloudflare Pages):** add **rewrites** so `/api` and `/outputs` forward to your API origin.

Example `vercel.json` at the **frontend repo root** (adjust `destination` to your real API URL):

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://YOUR-BACKEND.onrender.com/api/:path*"
    },
    {
      "source": "/outputs/:path*",
      "destination": "https://YOUR-BACKEND.onrender.com/outputs/:path*"
    }
  ]
}
```

Build command: `cd frontend && npm install && npm run build`  
Output directory: `frontend/dist`

Then set `CORS_ORIGINS` to your Vercel URL (e.g. `https://cinegraph.vercel.app`).

**Option B — Single origin:** serve the built SPA from the same FastAPI process (nginx in front, or mount `StaticFiles` on `/`). This repo does not include that wiring by default; Option A is usually faster for students.

## 7. Docker (full stack locally or on a VPS)

From the **repository root**:

```bash
docker compose up --build
```

- Backend: port **8000**, uses `backend/.env.example` unless you switch `env_file` to `backend/.env`.
- Frontend: port **5173**, dev server (not optimized production build).

For **production Docker**, prefer:

1. Multi-stage build for frontend → static files.  
2. One image running **uvicorn** only, with nginx/Caddy in front serving `dist/` and proxying `/api` → uvicorn — **or** use two services + rewrites as above.

The included `frontend/Dockerfile` runs `npm run dev` for convenience, not for high-traffic production.

## 8. Example: free-tier style split (outline)

These are typical patterns; exact clicks change when vendors update dashboards.

1. **Database:** Create a free Postgres (Neon, Supabase, or Render Postgres). Copy connection string → `DATABASE_URL`.
2. **Backend:** New Web Service from this repo’s `backend/` Dockerfile (Render/Fly/Railway). Set env vars; set health check to `GET /health`.
3. **Frontend:** Connect GitHub to Vercel; root = `frontend`; build `npm run build`; output `dist`; add `vercel.json` rewrites to backend URL.
4. **CORS:** `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`
5. **Outputs:** Add persistent disk mounted at `/app/outputs` with `OUTPUTS_DIR=/app/outputs`, or accept ephemeral storage for quick demos.

## 9. Health checks and operations

- **Liveness:** `GET /health` → `{"status":"ok"}`  
- **Logs:** JSON structured logs (see `app/logging_setup.py`); tune with `LOG_LEVEL`.
- **Timeouts:** Long compilations run in background; HTTP returns `202` on create. Clients should poll `GET /api/v1/jobs/{job_id}` or story status.

## 10. Security checklist

- Do not commit `backend/.env` or API keys (`.gitignore` already ignores `.env`).
- Use HTTPS everywhere in production.
- Rotate keys if they were ever pasted in chat or committed.
- Restrict `CORS_ORIGINS` to your real frontend URL(s), not `*`.

## 11. LLM in production

- **Groq** / **Anthropic** keys live only in the backend environment.
- `use_llm: false` from the client still works and avoids billing (heuristic pipeline).

## 12. Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Frontend `404` on `/api` | Rewrites not configured; frontend trying to call itself |
| CORS error in browser | `CORS_ORIGINS` missing frontend URL |
| `ModuleNotFoundError: psycopg2` | Install `psycopg2-binary` in the deployed environment |
| Video generation fails | Missing ffmpeg binary; `imageio-ffmpeg` usually bundles one — on minimal images, `apt-get install -y ffmpeg` in Dockerfile |
| DB locked / lost | SQLite on ephemeral disk; switch to Postgres + persistent URL |
| Storyboard URLs 404 | `OUTPUTS_DIR` not persistent or path mismatch |

## 13. Quick verification after deploy

```bash
curl -sS https://YOUR-API/health
curl -sS -X POST https://YOUR-API/api/v1/stories \
  -H "Content-Type: application/json" \
  -d '{"title":"Deploy test","input":"A short test narrative with enough characters for validation.","seed":1,"use_llm":false}'
```

Poll `job` until `completed`, then `GET .../storyboard` and open an `/outputs/...` URL in the browser.

---

For product-level test stories and demo scripting, see `files/SUBMISSION_TECH_NOTE_AND_TEST_PLAN.md`.

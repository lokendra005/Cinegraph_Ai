# CineGraph AI — Task 1 Submission: Narrative-to-Visual Story Agent

**Product positioning:** A deterministic multi-agent **narrative compilation engine** (screenplay + cinematic plan + storyboard + optional scene-film MP4), not a generic unconstrained text-to-video toy.

---

## Submission links (fill before submitting)

- **Live demo (frontend):** `https://cinegraph-ai.vercel.app/`  
- **Backend API (health check):** `https://cinegraph-ai.onrender.com/health`  
- **GitHub repository:** `https://github.com/lokendra005/Cinegraph_Ai` *(update if different)*  
- **Demo video:** [Loom recording](https://www.loom.com/share/032fb25afbd94c77b98777797a20aeed)

---

## 1) Architecture overview

CineGraph AI converts **free-form narrative text** into:

1. **Structured semantic state** (characters, locations, themes, ambiguity flags)  
2. **Scene plan** (locations, tone, transitions, pacing)  
3. **Screenplay layer** (slugline, synopsis, beats, dialogue, transition out) — **Scriptwriter agent**  
4. **Director / continuity / ambiguity** passes for cinematic consistency  
5. **Visual prompts** per storyboard frame (seeded, per-beat variation)  
6. **Storyboard frames** (deterministic **Pillow** placeholders; prompts are production-ready for a real image backend)  
7. **Evaluation metrics** (heuristic scoring for demo/regression)  
8. **Optional MP4 output** (“scene film”: slate + motion + crossfades + dialogue burn-in; **animatic/previz**, not bundled neural T2V)

**Core pipeline (orchestrated DAG):**

1. **Narrative Parser** — JSON narrative graph; detects ambiguities.  
2. **Scene Planner** — cinematic scene segmentation + metadata.  
3. **Scriptwriter** — screenplay fields per scene (dialogue, beats, slugline).  
4. **Director** — shot, lighting, palette, **pacing**.  
5. **Continuity** — cross-scene consistency notes.  
6. **Ambiguity Resolution** — automatic resolutions merged into narrative state.  
7. **Visual Prompt Generator** — positive/negative prompts, per-frame seeds/beats.  
8. **Storyboard generation** — renders PNGs under `outputs/{story_id}/`.  
9. **Evaluator** — alignment/continuity/ambiguity-style scores.

**Persistence:** SQLAlchemy (`stories`, `narrative_states`, `scenes`, `storyboard_frames`, `agent_logs`, `evaluation_results`, `compilation_jobs`). SQLite locally; **PostgreSQL** on Render via `DATABASE_URL`.

**Jobs:** `POST /api/v1/stories` returns `job_id`; compilation runs in background with **retries**; queued jobs can be **cancelled**.

**Observability:** Structured JSON logs; `x-request-id` and `x-response-time-ms` on API responses; agent logs in DB (trace API available for debugging).

**Deployment:** Frontend on **Vercel** with `vercel.json` rewrites for `/api` and `/outputs` → **Render** backend; see `DEPLOYMENT.md`.

---

## 2) Multilingual capability (bonus — optional extension)

The current MVP is **English-first** with deterministic heuristics and LLM providers (Groq/Anthropic) that *can* respond in other languages if the model follows the user’s language.

**To claim bonus credit in viva/demo:** show the same story submitted with a short **Hindi** (or mixed) paragraph and demonstrate that **structure** (scenes, script JSON, prompts) remains coherent. Full multilingual QA would add explicit language detection + prompts — listed as future work in trade-offs.

---

## 3) Design decisions and trade-offs

*(Full table in online Markdown viewers; PDF generator lists bullets below.)*

- **Multi-agent vs single LLM:** clearer responsibilities and traces; trade-off is higher latency than one-shot generation.  
- **Heuristic fallback (`use_llm: false`):** offline, CI-safe, deterministic; trade-off is less “creative” prose than full LLM.  
- **Placeholder frames (Pillow):** reliable, no GPU; trade-off is not photoreal (prompts are ready for a real image backend).  
- **Scene-film MP4 (imageio/ffmpeg):** meets “video or storyboard” without mandatory T2V APIs; trade-off is animatic quality, not neural Hollywood video.  
- **Postgres on Render + optional disk:** production-shaped DB; trade-off is free-tier ephemeral disk unless paid disk or object storage.  
- **Vercel rewrites:** same-origin `/api` for the SPA; trade-off is you must ship `vercel.json` and the correct backend URL.

| Decision | Why | Trade-off |
|----------|-----|-----------|
| **Multi-agent vs single LLM** | Clear responsibilities, traceable failures, rubric “depth of agent design”. | Higher latency than one-shot generation. |
| **Heuristic fallback (`use_llm: false`)** | Works offline, CI-safe, **deterministic** for evaluators without API keys. | Less “creative” prose than full LLM. |
| **Placeholder frames (Pillow)** | Reliable, no GPU/credits; meets storyboard requirement. | Not photoreal; prompts intended for downstream diffusion. |
| **Scene-film MP4 (imageio/ffmpeg)** | Satisfies “video or storyboard” without mandatory paid T2V APIs. | Animatic quality; not Hollywood neural video. |
| **Postgres on Render + optional disk** | Production-shaped DB; files under `/outputs` need persistence on cloud. | Free tier may use ephemeral disk — regenerate or download MP4 for demos. |
| **Vercel rewrites** | Same-origin `/api` from SPA without changing frontend fetch URLs. | Must ship `vercel.json` and correct backend URL. |

---

## 4) Test instructions for evaluators

### Setup (local)

```bash
git clone <repo-url>
cd Cinegraph_Ai/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd ../frontend && npm install && npm run dev
```

Open UI: `http://localhost:5173` — API docs: `http://localhost:8000/docs`.

### Live demo

1. Open **Live demo** URL.  
2. Paste a **predefined test story** (see section 5) or use UI presets.  
3. Optional: toggle **Use LLM** off for **fully reproducible** heuristic run.  
4. Click compile; wait for storyboard.  
5. Click **Generate full film** and/or **Scene MP4 only**; confirm playback.  
6. Optional: `GET /api/v1/stories/{id}/trace` for agent-level audit (API).

### Automated tests (repo)

```bash
cd backend && pytest tests/ -v
```

---

## 5) Predefined test stories and expected behavior

### A) Emotional drama

**Input:**  
*A retired astronaut receives radio messages from his dead co-pilot.*

**Expect:** Melancholic tone; isolation; emotional progression across scenes; script/dialogue grounded in premise; multiple scenes.

### B) Action / cyberpunk

**Input:**  
*A hacker infiltrates a floating cyberpunk city.*

**Expect:** Faster pacing language in metadata; neon/cyberpunk-flavored prompts; dynamic shot vocabulary.

### C) Ambiguous narrative

**Input:**  
*A woman opens a letter and begins crying silently.*

**Expect:** Ambiguity flagged in parsed state; ambiguity agent log; restrained cinematography in director metadata.

### Determinism check

Same text + same **seed** + `use_llm: false` → stable scene count, stable frame filenames under `outputs/{story_id}/`, similar planner/director fields.

---

## 6) Evaluation criteria mapping (Task 1)

| Criterion | How CineGraph addresses it |
|-----------|----------------------------|
| **Coherence** (story ↔ output) | Narrative state + scene plan + scriptwriter + continuity |
| **Scene breakdown quality** | Scene planner + director + per-scene script |
| **Ambiguous / unstructured input** | Parser ambiguity flags + ambiguity agent |
| **Determinism / reproducibility** | Seed propagation, heuristic mode, job retries |
| **Observability / testability** | Logs, request IDs, DB agent logs, pytest suite |
| **Deployment** | Docker, Render + Vercel, `DEPLOYMENT.md` |
| **Video** | Full film + per-scene MP4 (animatic) |

---

## 7) API surface (summary)

- `POST /api/v1/stories` — create story; returns `story_id`, `job_id`  
- `GET /api/v1/jobs/{job_id}` — job status  
- `GET/POST /api/v1/stories/{id}/video` — full MP4  
- `GET/POST /api/v1/stories/{id}/scenes/{scene_id}/video` — single-scene MP4  
- `GET /api/v1/stories/{id}/storyboard` — frame URLs under `/outputs/...`  
- Plus: scenes, evaluation, narrative-graph, regenerate, cancel (see README)

---

## 8) Final notes

CineGraph AI prioritizes:

- **Engineered** multi-agent decomposition over a single black-box prompt  
- **Explainable** artifacts (scenes, script, prompts, evaluation)  
- **Reliable** demo path (offline heuristics + hosted LLM optional)  
- **Assessment-aligned** outputs: script + visual plan + storyboard + **playable video**

For setup, tests, and deployment details, see the repository **README** and **DEPLOYMENT.md**.

---

*End of submission document (Markdown source). Generate PDF via `scripts/generate_submission_pdf.py` or print this file to PDF from your editor.*

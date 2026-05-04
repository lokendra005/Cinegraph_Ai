# CineGraph AI — Demo video script (60–120 seconds)

Use this as a **shot list + narration**. Record **1080p**, clear mic, slow mouse movements.

---

## Before you record

1. Use **live site** or local: frontend + backend running.  
2. Pick **one** test story (recommended: **Ambiguous** — “woman opens a letter…”).  
3. Set **Use LLM** as you prefer (for determinism demo, turn **off**).  
4. Close unrelated tabs; zoom browser to **100–125%** so text is readable.

---

## Shot 1 — Hook (0:00–0:15) **~15s**

**Screen:** Landing on CineGraph AI title.

**Say:**  
“This is **CineGraph AI** — a multi-agent system for **Task 1: Narrative to Visual Story**. It turns raw story text into a **structured screenplay**, a **cinematic scene plan**, **storyboard frames**, and an optional **MP4 scene film** — with **deterministic** offline mode for reproducibility.”

---

## Shot 2 — Input + compile (0:15–0:40) **~25s**

**Screen:** Story input panel.

**Do:** Paste the ambiguous letter story (or click preset). Show **seed** briefly.

**Say:**  
“I’m submitting **free-form narrative text**. I can fix a **random seed** so runs are repeatable — especially with **LLM off**, which uses our **heuristic pipeline** for stable evaluation.”

**Do:** Click **Compile** (or equivalent). Wait until status shows **completed** / storyboard appears.

**Say:**  
“The backend returns a **job id** and runs compilation in the background with **retries** for reliability.”

---

## Shot 3 — Outputs (0:40–1:15) **~35s**

**Screen:** Scroll **Scene timeline** and **Storyboard** — show synopsis, beats, dialogue, frame thumbnails.

**Say:**  
“Here’s the **scene breakdown** and **screenplay-style content**: slugline, beats, dialogue. Each frame has **distinct prompts** per beat. This satisfies the rubric: **script + visual plan + visual output**.”

**Do:** Click **Generate full film** (or scene MP4). Show **video playing**; optionally **Download**.

**Say:**  
“The **MP4** is an **animatic**: motion, transitions, and on-screen dialogue — not a paid neural text-to-video API, but a **credible video artifact** for the assignment.”

---

## Shot 4 — Determinism / API (1:15–1:30) **optional ~15s**

**Screen:** Either recompile same story same seed with LLM off, **or** open `https://<backend>/docs` and show `/health`.

**Say:**  
“Same seed and **use_llm false** gives **repeatable** structure; the API exposes **OpenAPI**, structured logging, and **request ids** for observability.”

---

## Closing line

**Say:**  
“Repo includes **pytest** coverage, **Docker**, and **deployment notes** for **Vercel + Render**. Thanks.”

---

## Recording on macOS (pick one)

### A) QuickTime Player (simplest)

1. **QuickTime Player** → **File** → **New Screen Recording**.  
2. Select window or full screen; enable mic if you narrate.  
3. Record → **Stop** → **File** → **Export** (720p or 1080p).  
4. Upload to Google Drive / YouTube (unlisted).

### B) OBS Studio (free, more control)

1. Download OBS; add **Display Capture** + **Audio Input Capture**.  
2. **Settings** → **Output** → recording quality **High**.  
3. **Start Recording** → run demo → **Stop Recording**.

### C) ffmpeg (terminal, advanced)

List devices:

```bash
ffmpeg -f avfoundation -list_devices true -i ""
```

Record screen + mic (device indices vary — replace `1` and `0` after listing):

```bash
ffmpeg -f avfoundation -i "1:0" -c:v h264_videotoolbox -c:a aac -y ~/Desktop/cinegraph_demo.mp4
```

Press `q` to stop.

---

## Checklist before upload

- [ ] Audio clear, no loud keyboard clacks  
- [ ] Story **completes** and **video plays** in the recording  
- [ ] At least one **scroll** through storyboard/script visible  
- [ ] Length **under 2 minutes** unless evaluator asked longer  
- [ ] Paste **demo link** into `CINEGRAPH_AI_TASK1_SUBMISSION_DOCUMENT.md` section 1  

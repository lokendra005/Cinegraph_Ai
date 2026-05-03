# CineGraph AI - Final Consolidated PRD

## 1) Product Vision

CineGraph AI is a deterministic multi-agent narrative compilation engine that turns free-form story input into:

- a structured screenplay
- a cinematic scene plan
- storyboard frames (required) and lightweight animation/video (optional)

It is intentionally positioned as an engineered storytelling system, not a generic text-to-video tool.

## 2) Evaluation-Aligned Objectives

This PRD is optimized for Task 1 (Narrative-to-Visual Story Agent) and maps directly to judging criteria:

- **Correctness and reliability**: schema validation, job retries, deterministic runs
- **Depth of agent design**: eight pipeline agents with explicit contracts (parser through evaluator)
- **Quality of outputs**: scene logic, continuity preservation, cinematic planning
- **Observability and testability**: trace logs, metrics, replay, predefined test stories
- **Deployment thinking**: clear API boundaries, worker separation, cloud-ready architecture

## 3) Scope

### In Scope (MVP)

1. Free-form story input (text; voice-to-text optional)
2. Structured screenplay generation
3. Scene-by-scene visual plan
4. Storyboard frame generation (1-3 frames per scene)
5. Deterministic reproducibility (same story + same seed)
6. Agent trace logging and evaluation metrics
7. Scene-film MP4 output (full story and per-scene clips: slates, motion, crossfades, dialogue burn-in)

### Stretch Scope

- Photoreal or neural text-to-video (not bundled; would use an external API)
- Multi-language stories (English + Hindi)
- Interactive ambiguity clarification loop

### Out of Scope

- photorealistic cinema-grade rendering
- end-to-end voice dubbing
- Hollywood-quality animation

## 4) System Architecture

```text
User Input
  -> Narrative Parser Agent
  -> Narrative State Engine
  -> Scene Planner Agent
  -> Scriptwriter Agent (screenplay: slugline, beats, dialogue)
  -> Director Agent
  -> Continuity Agent
  -> Ambiguity Resolution Agent
  -> Visual Prompt Generator Agent
  -> Storyboard Generation Engine
  -> Evaluation Agent
  -> Frontend Renderer + Trace Viewer (+ optional scene-film video export)
```

## 5) Agent Architecture (Final)

### 5.1 Narrative Parser Agent

**Goal:** Convert raw narrative to normalized semantic state.

**Input:** free-form story text  
**Output (validated JSON):**

- title, genre
- characters and relationships
- locations, timeline/events
- emotional arcs/conflicts/themes
- ambiguity flags

### 5.2 Scene Planner Agent

**Goal:** Convert narrative state into cinematic scenes.

**Output per scene:**

- scene_id, title, location, time_of_day
- characters_present
- scene_goal, emotional_tone
- transition_type, duration_estimate
- visual_priority

### 5.3 Scriptwriter Agent

**Goal:** Turn each planned scene into screenplay-ready text.

**Output per scene (JSON):**

- slugline (INT./EXT. style)
- synopsis (short dramatic summary)
- beats (ordered story beats)
- dialogues (speaker + line; at least two lines per scene when LLM is enabled)
- transition_out (CUT TO, DISSOLVE TO, etc.)

### 5.4 Director Agent

**Goal:** Produce cinematic decisions for each scene.

**Output:**

- camera_angle, shot_type
- lighting, color_palette
- mood, pacing, cinematic_style

### 5.5 Continuity Agent

**Goal:** Preserve cross-scene consistency.

Tracks:

- character appearance (hair/clothing/injury/accessories)
- emotional progression
- environment continuity (weather, props, damage, lighting)

Raises continuity violations when state changes are unjustified.

### 5.6 Ambiguity Resolution Agent

**Goal:** Resolve vague narrative segments.

Modes:

- **Auto mode**: context-based inference
- **Interactive mode**: asks user clarifying options

### 5.7 Visual Prompt Generator Agent

**Goal:** Generate style-consistent prompts for image synthesis.

**Output:**

- positive_prompt
- negative_prompt
- style_reference
- aspect_ratio
- seed

### 5.8 Evaluation Agent

**Goal:** Grade output quality and support regression testing.

**Metrics (0-1):**

- narrative_alignment_score
- continuity_score
- visual_consistency_score
- ambiguity_resolution_score

## 6) Narrative State Engine (Core)

The state engine is immutable and versioned. Each agent consumes a state version and emits a new version.

State includes:

- story metadata
- per-scene plans
- character state timeline
- continuity log
- prompt and generation metadata

This design enables replay, auditability, and deterministic debugging.

## 7) Determinism Contract

Determinism is mandatory, not optional.

Controls:

- fixed model temperature (`0.2-0.3`)
- explicit seed propagation across all non-LLM randomness
- schema-first outputs (Pydantic/JSON schema)
- stable orchestration order (DAG with pinned execution graph)
- saved prompts + saved model/version metadata

Expected behavior:

- same narrative + config + seed -> near-identical scene plans and prompts
- storyboard outputs are reproducible within model variance bounds

## 8) Data Model (Minimum Required)

Required tables:

- `stories`
- `narrative_states`
- `scenes`
- `character_states`
- `cinematic_decisions`
- `visual_prompts`
- `storyboard_frames`
- `agent_logs`
- `evaluation_results`
- `compilation_jobs` (durable compile jobs: status, retries, cancellation)

## 9) API Surface (MVP)

- `POST /api/v1/stories` -> create story and queue compilation (returns `story_id`, `job_id`)
- `GET /api/v1/jobs/{job_id}` -> job status
- `POST /api/v1/jobs/{job_id}/cancel` -> cancel queued job
- `GET /api/v1/stories/{story_id}` -> story status + metadata
- `GET /api/v1/stories/{story_id}/scenes` -> scene plan (+ script metadata)
- `GET /api/v1/stories/{story_id}/storyboard` -> generated frames
- `GET|POST /api/v1/stories/{story_id}/video` -> full cinematic MP4 (scene slates + motion + dissolves)
- `GET|POST /api/v1/stories/{story_id}/scenes/{scene_id}/video` -> single-scene MP4
- `GET /api/v1/stories/{story_id}/trace` -> agent logs + timings
- `GET /api/v1/stories/{story_id}/evaluation` -> quality metrics
- `GET /api/v1/stories/{story_id}/narrative-graph` -> graph JSON
- `GET /api/v1/stories/{story_id}/jobs` -> job history
- `POST /api/v1/stories/{story_id}/regenerate` -> rerun with seed (returns `job_id`)

## 10) Frontend Requirements

Implemented UI:

1. **Story Input Panel** (text, presets, seed, LLM toggle)
2. **Scene Timeline Viewer** (planner/director tags, locations)
3. **Storyboard Viewer** (scene-first layout: synopsis, beats, dialogue, clickable frames + prompt modal)
4. **Agent Trace Viewer** (execution logs in the main panel flow)
5. **Narrative Graph** (API + UI consumption as provided)
6. **Job history** and cancel for queued compilation jobs
7. **Video** (full film + per-scene MP4 generation, inline players, download links)

## 11) Testing Plan (Evaluator Ready)

Use at least 3 predefined stories:

1. **Emotional drama**  
   "A retired astronaut receives radio messages from his dead co-pilot."
2. **Action narrative**  
   "A hacker infiltrates a floating cyberpunk city."
3. **Ambiguous narrative**  
   "A woman opens a letter and begins crying silently."

For each test, validate:

- coherent scene decomposition
- cinematic logic alignment
- continuity persistence
- ambiguity handling quality
- deterministic replay across 3 reruns

## 12) Deployment Plan

Recommended:

- Frontend: Vercel
- Backend API: Railway/Render
- Worker/Image generation: Modal/RunPod/Replicate
- DB: PostgreSQL
- Storage: S3 or local object storage for MVP

## 13) Delivery Checklist (Internship Submission)

Required:

- technical note (architecture, decisions, trade-offs)
- reproducible test instructions
- 3 predefined stories with expected characteristics
- demo video

Optional but valuable:

- live deployed interface
- multilingual support demo

## 14) Positioning Statement

**CineGraph AI is a deterministic multi-agent cinematic narrative compilation engine.**

This framing differentiates the project from generic text-to-image/video demos and highlights system design maturity, reliability, and observability.

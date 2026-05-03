from __future__ import annotations

from datetime import datetime, timezone
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.pipeline_runner import clear_generated, run_full_pipeline
from app.config import get_settings
from app.database import get_db
from app.models import AgentLog, CompilationJob, EvaluationResult, NarrativeState, Scene, Story, StoryboardFrame
from app.schemas.api import (
    JobActionResponse,
    JobStatusResponse,
    RegenerateRequest,
    StoryCreateRequest,
    StoryCreateResponse,
    StoryRegenerateResponse,
)
from app.services.video_render import SceneFilmInput, build_cinematic_story_video, build_single_scene_film

router = APIRouter(prefix="/api/v1", tags=["stories"])


def _scene_film_input(story: Story, scene: Scene, db: Session) -> SceneFilmInput:
    settings = get_settings()
    meta = scene.metadata_json or {}
    script = meta.get("script") if isinstance(meta.get("script"), dict) else {}
    frames = (
        db.query(StoryboardFrame)
        .filter(StoryboardFrame.scene_id == scene.id)
        .order_by(StoryboardFrame.frame_index)
        .all()
    )
    paths = [settings.outputs_dir / f.image_path for f in frames]
    return SceneFilmInput(
        scene_number=scene.scene_number,
        title=scene.title,
        script=script,
        frame_paths=paths,
        motion_seed=story.seed,
    )


def _scene_film_rel(story_id: str, scene_number: int) -> str:
    return f"{story_id}/scene_{scene_number:02d}_film.mp4"


def _run_compilation_job(job_id: str) -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.query(CompilationJob).filter(CompilationJob.id == job_id).first()
        if not job:
            return
        max_attempts = max(1, job.max_attempts or 1)
        while (job.attempts or 0) < max_attempts:
            db.refresh(job)
            if job.status == "cancelled":
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
                return

            job.status = "running"
            if not job.started_at:
                job.started_at = datetime.now(timezone.utc)
            job.attempts = (job.attempts or 0) + 1
            db.commit()

            try:
                run_full_pipeline(db, job.story_id, use_llm=job.use_llm)
                story = db.query(Story).filter(Story.id == job.story_id).first()
                if story and story.status == "completed":
                    job.status = "completed"
                    job.last_error = None
                    job.finished_at = datetime.now(timezone.utc)
                    db.commit()
                    return
                err = story.error_message if story else "Story not found after run"
                job.last_error = err
            except Exception as exc:
                job.last_error = str(exc)

            if (job.attempts or 0) >= max_attempts:
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                db.commit()
                return
            # Lightweight bounded backoff before retry.
            sleep_s = min(2, 0.2 * (2 ** ((job.attempts or 1) - 1)))
            db.commit()
            time.sleep(sleep_s)
    except Exception as exc:
        job = db.query(CompilationJob).filter(CompilationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.last_error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/stories", response_model=StoryCreateResponse, status_code=202)
def create_story(
    body: StoryCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> StoryCreateResponse:
    story = Story(
        title=body.title,
        raw_input=body.input,
        input_type=body.input_type,
        status="processing",
        seed=body.seed,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    job = CompilationJob(
        story_id=story.id,
        status="queued",
        attempts=0,
        max_attempts=2,
        use_llm=body.use_llm,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_run_compilation_job, job.id)
    return StoryCreateResponse(story_id=story.id, job_id=job.id, status="processing")


@router.get("/stories/{story_id}")
def get_story(story_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    ns = db.query(NarrativeState).filter(NarrativeState.story_id == story_id).first()
    return {
        "id": story.id,
        "title": story.title,
        "status": story.status,
        "seed": story.seed,
        "error_message": story.error_message,
        "created_at": story.created_at.isoformat(),
        "parsed": ns.parsed_data if ns else None,
    }


@router.get("/stories/{story_id}/scenes")
def get_scenes(story_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    scenes = db.query(Scene).filter(Scene.story_id == story_id).order_by(Scene.scene_number).all()
    return [
        {
            "id": s.id,
            "scene_number": s.scene_number,
            "title": s.title,
            "location": s.location,
            "metadata": s.metadata_json,
        }
        for s in scenes
    ]


@router.get("/stories/{story_id}/storyboard")
def get_storyboard(story_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    scenes = db.query(Scene).filter(Scene.story_id == story_id).order_by(Scene.scene_number).all()
    out: list[dict[str, Any]] = []
    for s in scenes:
        frames = db.query(StoryboardFrame).filter(StoryboardFrame.scene_id == s.id).order_by(StoryboardFrame.frame_index).all()
        out.append(
            {
                "scene_id": s.id,
                "scene_number": s.scene_number,
                "title": s.title,
                "frames": [
                    {
                        "frame_index": f.frame_index,
                        "url": f"/outputs/{f.image_path}",
                        "prompt_meta": f.prompt_meta,
                    }
                    for f in frames
                ],
            }
        )
    return {"story_id": story_id, "scenes": out}


@router.get("/stories/{story_id}/video")
def get_story_video(story_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    settings = get_settings()
    rel = f"{story_id}/storyboard_video.mp4"
    fp = settings.outputs_dir / rel
    scenes = db.query(Scene).filter(Scene.story_id == story_id).order_by(Scene.scene_number).all()
    scene_clips: list[dict[str, Any]] = []
    for s in scenes:
        srel = _scene_film_rel(story_id, s.scene_number)
        if (settings.outputs_dir / srel).exists():
            scene_clips.append(
                {
                    "scene_id": s.id,
                    "scene_number": s.scene_number,
                    "video_url": f"/outputs/{srel}",
                }
            )
    return {
        "story_id": story_id,
        "ready": fp.exists(),
        "video_url": f"/outputs/{rel}" if fp.exists() else None,
        "video_kind": "cinematic_scene_film",
        "scene_clips": scene_clips,
    }


@router.post("/stories/{story_id}/video")
def generate_story_video(story_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    scenes = db.query(Scene).filter(Scene.story_id == story_id).order_by(Scene.scene_number).all()
    if not scenes:
        raise HTTPException(status_code=400, detail="No scenes available to render video")

    settings = get_settings()
    inputs = [_scene_film_input(story, s, db) for s in scenes]
    rel = f"{story_id}/storyboard_video.mp4"
    out_path = settings.outputs_dir / rel
    written = build_cinematic_story_video(inputs, out_path)
    return {
        "story_id": story_id,
        "video_url": f"/outputs/{rel}",
        "frames_written": written,
        "video_kind": "cinematic_scene_film",
    }


@router.get("/stories/{story_id}/scenes/{scene_id}/video")
def get_scene_video(story_id: str, scene_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    scene = db.query(Scene).filter(Scene.id == scene_id, Scene.story_id == story_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    settings = get_settings()
    rel = _scene_film_rel(story_id, scene.scene_number)
    fp = settings.outputs_dir / rel
    return {
        "story_id": story_id,
        "scene_id": scene.id,
        "scene_number": scene.scene_number,
        "ready": fp.exists(),
        "video_url": f"/outputs/{rel}" if fp.exists() else None,
        "video_kind": "scene_film",
    }


@router.post("/stories/{story_id}/scenes/{scene_id}/video")
def generate_scene_video(story_id: str, scene_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    scene = db.query(Scene).filter(Scene.id == scene_id, Scene.story_id == story_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    settings = get_settings()
    inp = _scene_film_input(story, scene, db)
    if not [p for p in inp.frame_paths if p.exists()]:
        raise HTTPException(status_code=400, detail="No storyboard frames for this scene")
    rel = _scene_film_rel(story_id, scene.scene_number)
    out_path = settings.outputs_dir / rel
    written = build_single_scene_film(inp, out_path)
    return {
        "story_id": story_id,
        "scene_id": scene.id,
        "video_url": f"/outputs/{rel}",
        "frames_written": written,
        "video_kind": "scene_film",
    }


@router.get("/stories/{story_id}/trace")
def get_trace(story_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    logs = db.query(AgentLog).filter(AgentLog.story_id == story_id).order_by(AgentLog.created_at).all()
    return {
        "story_id": story_id,
        "agents": [
            {
                "agent_name": L.agent_name,
                "status": L.status,
                "execution_time_ms": L.execution_time_ms,
                "created_at": L.created_at.isoformat(),
                "input": L.input_json,
                "output": L.output_json,
                "error": L.error,
            }
            for L in logs
        ],
    }


@router.get("/stories/{story_id}/evaluation")
def get_evaluation(story_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    ev = db.query(EvaluationResult).filter(EvaluationResult.story_id == story_id).first()
    if not ev:
        return {"story_id": story_id, "status": "pending"}
    return {
        "story_id": story_id,
        "overall_score": ev.overall_score,
        "metrics": ev.metrics,
    }


@router.get("/stories/{story_id}/narrative-graph")
def narrative_graph(story_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    ns = db.query(NarrativeState).filter(NarrativeState.story_id == story_id).first()
    scenes = db.query(Scene).filter(Scene.story_id == story_id).order_by(Scene.scene_number).all()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    chars: dict[str, str] = {}
    if ns and ns.parsed_data:
        for c in ns.parsed_data.get("characters") or []:
            name = c.get("name")
            if name:
                cid = f"character:{name}"
                chars[name] = cid
                nodes.append({"id": cid, "type": "character", "label": name})
    prev_sid: str | None = None
    for s in scenes:
        sid = f"scene:{s.id}"
        tone = (s.metadata_json or {}).get("planner", {}).get("emotional_tone", "")
        nodes.append(
            {
                "id": sid,
                "type": "scene",
                "label": s.title,
                "scene_number": s.scene_number,
                "emotional_tone": tone,
            }
        )
        if prev_sid:
            tr = (s.metadata_json or {}).get("planner", {}).get("transition_type", "cut")
            edges.append({"source": prev_sid, "target": sid, "type": "transition", "transition": tr})
        prev_sid = sid
        for name in (s.metadata_json or {}).get("planner", {}).get("characters_present") or []:
            cid = chars.get(name)
            if cid:
                edges.append({"source": cid, "target": sid, "type": "appears_in"})
    return {"story_id": story_id, "nodes": nodes, "edges": edges}


@router.get("/stories/{story_id}/jobs", response_model=list[JobStatusResponse])
def get_story_jobs(story_id: str, db: Session = Depends(get_db)) -> list[JobStatusResponse]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    jobs = (
        db.query(CompilationJob)
        .filter(CompilationJob.story_id == story_id)
        .order_by(CompilationJob.created_at.desc())
        .all()
    )
    return [
        JobStatusResponse(
            id=job.id,
            story_id=job.story_id,
            status=job.status,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            use_llm=bool(job.use_llm),
            last_error=job.last_error,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.finished_at.isoformat() if job.finished_at else None,
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = db.query(CompilationJob).filter(CompilationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        id=job.id,
        story_id=job.story_id,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        use_llm=bool(job.use_llm),
        last_error=job.last_error,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobActionResponse)
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> JobActionResponse:
    job = db.query(CompilationJob).filter(CompilationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "queued":
        raise HTTPException(
            status_code=409,
            detail=f"Job cannot be cancelled in status '{job.status}'",
        )
    job.status = "cancelled"
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    story = db.query(Story).filter(Story.id == job.story_id).first()
    if story and story.status == "processing":
        story.status = "failed"
        story.error_message = "Job cancelled"
        db.commit()
    return JobActionResponse(job_id=job.id, status="cancelled")


@router.post("/stories/{story_id}/regenerate", response_model=StoryRegenerateResponse, status_code=202)
def regenerate(
    story_id: str,
    body: RegenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> StoryRegenerateResponse:
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.seed = body.seed
    story.status = "processing"
    story.error_message = None
    db.commit()
    clear_generated(db, story_id)
    job = CompilationJob(
        story_id=story.id,
        status="queued",
        attempts=0,
        max_attempts=2,
        use_llm=body.use_llm,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_run_compilation_job, job.id)
    return StoryRegenerateResponse(story_id=story_id, job_id=job.id, status="processing")

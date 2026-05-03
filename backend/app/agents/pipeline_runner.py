from __future__ import annotations

import time
from datetime import datetime, timezone
import shutil
from typing import Any

from sqlalchemy.orm import Session

from app.agents.ambiguity import run_ambiguity
from app.agents.continuity import run_continuity
from app.agents.director import run_director
from app.agents.evaluator import run_evaluator
from app.agents.narrative_parser import run_parser
from app.agents.prompt_gen import run_prompt_gen
from app.agents.scene_planner import run_planner
from app.agents.scriptwriter import run_scriptwriter
from app.config import get_settings
from app.models import AgentLog, EvaluationResult, NarrativeState, Scene, Story, StoryboardFrame
from app.services.storyboard_render import render_placeholder_frame


def _log(
    db: Session,
    story_id: str,
    agent_name: str,
    status: str,
    input_json: dict[str, Any] | None,
    output_json: dict[str, Any] | None,
    ms: int | None,
    error: str | None = None,
) -> None:
    db.add(
        AgentLog(
            story_id=story_id,
            agent_name=agent_name,
            status=status,
            input_json=input_json,
            output_json=output_json,
            execution_time_ms=ms,
            error=error,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()


def clear_generated(db: Session, story_id: str) -> None:
    settings = get_settings()
    db.query(Scene).filter(Scene.story_id == story_id).delete()
    db.query(AgentLog).filter(AgentLog.story_id == story_id).delete()
    db.query(EvaluationResult).filter(EvaluationResult.story_id == story_id).delete()
    db.query(NarrativeState).filter(NarrativeState.story_id == story_id).delete()
    db.commit()
    out_dir = settings.outputs_dir / story_id
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)


def run_full_pipeline(db: Session, story_id: str, use_llm: bool | None = None) -> None:
    settings = get_settings()
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        return
    if use_llm is None:
        use_llm = bool(settings.anthropic_api_key)

    story.status = "processing"
    story.error_message = None
    db.commit()

    try:
        t0 = time.perf_counter()
        parsed = run_parser(story.raw_input, use_llm=use_llm)
        _log(
            db,
            story_id,
            "narrative_parser",
            "success",
            {"use_llm": use_llm},
            {"keys": list(parsed.keys()), "title": parsed.get("title")},
            int((time.perf_counter() - t0) * 1000),
        )

        ns = NarrativeState(story_id=story_id, version=1, parsed_data=parsed)
        db.add(ns)
        db.commit()

        t0 = time.perf_counter()
        scenes = run_planner(story.raw_input, parsed, story.seed, use_llm=use_llm)
        _log(
            db,
            story_id,
            "scene_planner",
            "success",
            {"scene_count": len(scenes)},
            {"scene_ids": [s.get("scene_id") for s in scenes]},
            int((time.perf_counter() - t0) * 1000),
        )

        t0 = time.perf_counter()
        scripts = run_scriptwriter(scenes, use_llm=use_llm)
        _log(
            db,
            story_id,
            "scriptwriter",
            "success",
            {"scenes": len(scenes)},
            {"scripts": len(scripts), "sample_slugline": scripts[0].get("slugline") if scripts else None},
            int((time.perf_counter() - t0) * 1000),
        )

        t0 = time.perf_counter()
        directives = run_director(scenes, use_llm=use_llm)
        _log(
            db,
            story_id,
            "director",
            "success",
            {"directives": len(directives)},
            {"sample": directives[0] if directives else {}},
            int((time.perf_counter() - t0) * 1000),
        )

        t0 = time.perf_counter()
        continuity = run_continuity(scenes, parsed, directives)
        _log(
            db,
            story_id,
            "continuity",
            "success",
            {},
            {"violations": len(continuity.get("violations", []))},
            int((time.perf_counter() - t0) * 1000),
        )

        t0 = time.perf_counter()
        resolutions = run_ambiguity(parsed, use_llm=use_llm)
        parsed["ambiguity_resolutions"] = resolutions
        ns.parsed_data = parsed
        db.commit()
        _log(
            db,
            story_id,
            "ambiguity",
            "success",
            {"ambiguity_count": len(parsed.get("ambiguities") or [])},
            {"resolutions": len(resolutions)},
            int((time.perf_counter() - t0) * 1000),
        )

        style = f"{parsed.get('genre', 'drama')} storyboard, consistent character silhouettes"

        out_dir = settings.outputs_dir / story_id
        if out_dir.exists():
            for p in out_dir.glob("*.png"):
                p.unlink()

        for i, sc in enumerate(scenes):
            scene_number = i + 1
            dr = directives[i] if i < len(directives) else {}
            cont = continuity["per_scene"][i] if i < len(continuity["per_scene"]) else {}
            script = scripts[i] if i < len(scripts) else {}

            meta: dict[str, Any] = {
                "planner": {k: v for k, v in sc.items() if k != "body_text"},
                "planner_body": sc.get("body_text", ""),
                "script": script,
                "director": dr,
                "continuity": cont,
                "visual_prompt": {},
            }
            scene_row = Scene(
                story_id=story_id,
                scene_number=scene_number,
                title=sc.get("scene_title", f"Scene {scene_number}"),
                location=sc.get("location"),
                metadata_json=meta,
            )
            db.add(scene_row)
            db.flush()

            for fi in range(2):
                frame_seed = story.seed + i * 9973 + fi * 137
                sc_enriched = dict(sc)
                if script:
                    sc_enriched["script_excerpt"] = script.get("synopsis", "")
                    sc_enriched["dialogue_excerpt"] = " ".join(
                        [f"{d.get('speaker')}: {d.get('line')}" for d in (script.get("dialogues") or [])[:2]]
                    )
                vp = run_prompt_gen(sc_enriched, dr, frame_seed, style, frame_index=fi, total_frames=2)
                if fi == 0:
                    meta["visual_prompt"] = vp
                fname = f"scene_{scene_number:02d}_frame_{fi+1}.png"
                fpath = out_dir / fname
                subtitle = f"{vp.get('frame_beat', '')}: {script.get('synopsis', sc.get('scene_goal', ''))}"
                render_placeholder_frame(
                    fpath,
                    title=sc.get("scene_title", ""),
                    scene_number=scene_number,
                    frame_index=fi,
                    seed=frame_seed,
                    subtitle=subtitle[:160],
                )
                rel_image = f"{story_id}/{fname}"
                db.add(
                    StoryboardFrame(
                        scene_id=scene_row.id,
                        frame_index=fi,
                        image_path=rel_image,
                        prompt_meta=vp,
                    )
                )
        db.commit()

        t0 = time.perf_counter()
        metrics = run_evaluator(story.raw_input, parsed, scenes, continuity)
        overall = sum(
            metrics[k]
            for k in (
                "narrative_alignment_score",
                "continuity_score",
                "visual_consistency_score",
                "ambiguity_handling_score",
            )
        ) / 4
        db.add(
            EvaluationResult(
                story_id=story_id,
                metrics=metrics,
                overall_score=round(overall, 3),
            )
        )
        db.commit()
        _log(
            db,
            story_id,
            "evaluator",
            "success",
            {},
            {"overall_score": round(overall, 3)},
            int((time.perf_counter() - t0) * 1000),
        )

        _log(
            db,
            story_id,
            "storyboard_generation",
            "success",
            {"frames_per_scene": 2},
            {"output_dir": str(out_dir.resolve())},
            0,
        )

        story.status = "completed"
        db.commit()
    except Exception as e:
        story.status = "failed"
        story.error_message = str(e)
        db.commit()
        _log(db, story_id, "pipeline", "failed", {}, {}, None, error=str(e))

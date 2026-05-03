from __future__ import annotations

import json
from typing import Any

from app.agents.heuristic import director_preset
from app.services.llm import call_claude_json

DIR_SYSTEM = """You are the Director Agent. Given scenes, return ONLY JSON: {"directives": [...]}.
Each element must align by index with input scenes and have keys:
camera_angle, shot_type, lighting, color_palette, mood, cinematic_style, pacing.
Be concise; choices must fit emotional_tone of that scene."""


def run_director(scenes: list[dict[str, Any]], use_llm: bool) -> list[dict[str, Any]]:
    if use_llm and scenes:
        try:
            slim = [
                {
                    "scene_id": s.get("scene_id"),
                    "emotional_tone": s.get("emotional_tone"),
                    "scene_goal": s.get("scene_goal"),
                }
                for s in scenes
            ]
            out = call_claude_json(DIR_SYSTEM, json.dumps(slim)[:12000])
            directives = out.get("directives") or []
            if isinstance(directives, list) and len(directives) == len(scenes):
                return directives
        except Exception:
            pass
    return [director_preset(i, str(s.get("emotional_tone", ""))) for i, s in enumerate(scenes)]

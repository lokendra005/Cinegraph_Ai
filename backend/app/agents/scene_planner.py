from __future__ import annotations

import json
from typing import Any

from app.agents.heuristic import heuristic_plan_scenes
from app.services.llm import call_claude_json

PLAN_SYSTEM = """You are the Scene Planner. Return ONLY JSON: {"scenes": [scene objects]}.
Each scene object must have keys:
scene_id, scene_title, location, time_of_day, characters_present (string array),
scene_goal, emotional_tone, transition_type, duration_estimate, visual_priority, body_text (excerpt from narrative for this scene).
3 to 8 scenes. Preserve story order."""


def run_planner(narrative: str, parsed: dict[str, Any], seed: int, use_llm: bool) -> list[dict[str, Any]]:
    if use_llm:
        try:
            user = f"Seed (for stable choices): {seed}\nParsed narrative JSON:\n{json.dumps(parsed)[:12000]}\n\nFull narrative:\n{narrative[:12000]}"
            out = call_claude_json(PLAN_SYSTEM, user)
            scenes = out.get("scenes") or []
            if isinstance(scenes, list) and scenes:
                return scenes
        except Exception:
            pass
    return heuristic_plan_scenes(narrative, parsed, seed)

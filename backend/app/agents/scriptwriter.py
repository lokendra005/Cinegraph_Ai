from __future__ import annotations

import json
from typing import Any

from app.services.llm import call_claude_json

SCRIPT_SYSTEM = """You are the Scriptwriter Agent for CineGraph AI.
Return ONLY JSON in this format:
{
  "scripts": [
    {
      "scene_id": "scene_01",
      "slugline": "INT./EXT. location - time",
      "synopsis": "2-3 sentence dramatic scene summary",
      "beats": ["beat 1", "beat 2", "beat 3"],
      "dialogues": [
        {"speaker": "Name", "line": "Dialogue line"}
      ],
      "transition_out": "CUT TO|DISSOLVE TO|FADE OUT|MATCH CUT TO"
    }
  ]
}
Rules:
- 1 script object for each input scene, aligned by order.
- Keep dialogues grounded in story, concise and cinematic.
- Include at least 2 dialogue lines per scene.
"""


def _heuristic_script(scene: dict[str, Any], idx: int) -> dict[str, Any]:
    chars = scene.get("characters_present") or ["Protagonist"]
    c1 = chars[0] if chars else "Protagonist"
    c2 = chars[1] if len(chars) > 1 else "Inner Voice"
    tone = str(scene.get("emotional_tone", "tense"))
    goal = str(scene.get("scene_goal", ""))
    location = str(scene.get("location", "Unknown location"))
    tod = str(scene.get("time_of_day", "day"))
    trans = str(scene.get("transition_type", "cut")).upper()
    transition_out = {
        "CUT": "CUT TO",
        "DISSOLVE": "DISSOLVE TO",
        "FADE": "FADE OUT",
        "MONTAGE": "MATCH CUT TO",
        "FLASHBACK": "DISSOLVE TO",
    }.get(trans, "CUT TO")
    return {
        "scene_id": scene.get("scene_id", f"scene_{idx+1:02d}"),
        "slugline": f"INT./EXT. {location} - {tod.upper()}",
        "synopsis": f"In a {tone} moment, the scene advances the narrative through {goal[:160]}. Emotional stakes rise as choices become irreversible.",
        "beats": [
            f"Establish {location} and emotional tone ({tone}).",
            f"Conflict surfaces around: {goal[:120]}.",
            "Scene closes on a visual hook for transition.",
        ],
        "dialogues": [
            {"speaker": c1, "line": "I can't ignore this anymore."},
            {"speaker": c2, "line": "Then stop hiding from what it means."},
        ],
        "transition_out": transition_out,
    }


def run_scriptwriter(scenes: list[dict[str, Any]], use_llm: bool) -> list[dict[str, Any]]:
    if not scenes:
        return []
    if use_llm:
        try:
            user = json.dumps(
                [
                    {
                        "scene_id": s.get("scene_id"),
                        "location": s.get("location"),
                        "time_of_day": s.get("time_of_day"),
                        "characters_present": s.get("characters_present"),
                        "scene_goal": s.get("scene_goal"),
                        "emotional_tone": s.get("emotional_tone"),
                        "transition_type": s.get("transition_type"),
                    }
                    for s in scenes
                ]
            )
            out = call_claude_json(SCRIPT_SYSTEM, user)
            scripts = out.get("scripts") or []
            if isinstance(scripts, list) and len(scripts) == len(scenes):
                return scripts
        except Exception:
            pass
    return [_heuristic_script(s, i) for i, s in enumerate(scenes)]


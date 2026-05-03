from __future__ import annotations

from typing import Any


def run_continuity(
    scenes: list[dict[str, Any]], parsed: dict[str, Any], directives: list[dict[str, Any]]
) -> dict[str, Any]:
    char_names = [c.get("name") for c in parsed.get("characters", []) if c.get("name")]
    per_scene = []
    violations = []
    prev_props: dict[str, str] = {}
    for i, s in enumerate(scenes):
        present = set(s.get("characters_present") or [])
        missing_main = [n for n in char_names[:2] if n and n not in present and i > 0]
        if missing_main and i < len(scenes) - 1:
            violations.append(
                {
                    "scene_index": i,
                    "type": "character_presence",
                    "detail": f"Expected primary characters may be absent: {missing_main}",
                }
            )
        emotional = s.get("emotional_tone", "")
        _dir = directives[i] if i < len(directives) else {}
        state = {
            "appearance_notes": "consistent wardrobe unless script indicates change",
            "emotion": emotional,
            "cinematic_mood": _dir.get("mood", emotional),
            "props": prev_props.copy(),
        }
        if "flashlight" in str(s.get("scene_goal", "")).lower():
            prev_props["held_object"] = "flashlight"
        if "bleeding" in str(s.get("scene_goal", "")).lower() or "blood" in str(s.get("scene_goal", "")).lower():
            prev_props["injury"] = "visible injury until treated"
            if i + 1 < len(scenes):
                nxt = scenes[i + 1]
                if "heal" not in str(nxt.get("scene_goal", "")).lower() and "injury" not in str(
                    nxt.get("scene_goal", "")
                ).lower():
                    violations.append(
                        {
                            "scene_index": i + 1,
                            "type": "injury_continuity",
                            "detail": "Prior scene introduced injury; verify next scene preserves or resolves it.",
                        }
                    )
        per_scene.append({"scene_id": s.get("scene_id"), "character_state": state})
    return {"per_scene": per_scene, "violations": violations}

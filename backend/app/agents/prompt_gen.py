from __future__ import annotations

from typing import Any


def run_prompt_gen(
    scene: dict[str, Any],
    director: dict[str, Any],
    seed: int,
    style: str,
    frame_index: int = 0,
    total_frames: int = 2,
) -> dict[str, Any]:
    loc = scene.get("location", "")
    tone = scene.get("emotional_tone", "")
    goal = scene.get("scene_goal", "")
    script_excerpt = scene.get("script_excerpt", "")
    dialogue_excerpt = scene.get("dialogue_excerpt", "")
    beat = (
        "opening composition"
        if frame_index == 0
        else ("moment escalation" if frame_index < total_frames - 1 else "closing composition")
    )
    pos = (
        f"Cinematic storyboard frame, {style}, {director.get('shot_type')} {director.get('camera_angle')} shot. "
        f"Location: {loc}. Mood: {tone}. Lighting: {director.get('lighting')}. Palette: {director.get('color_palette')}. "
        f"Frame beat: {beat}. Scene action: {goal}. Script intent: {script_excerpt}. Dialogue cue: {dialogue_excerpt}. "
        "High detail composition, film grain subtle."
    )
    neg = "text, watermark, logo, deformed hands, extra fingers, low resolution, blurry faces"
    return {
        "positive_prompt": pos,
        "negative_prompt": neg,
        "style_reference": style,
        "aspect_ratio": "16:9",
        "seed": seed,
        "frame_index": frame_index,
        "frame_beat": beat,
    }

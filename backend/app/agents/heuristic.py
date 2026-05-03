from __future__ import annotations

import re
from typing import Any


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _title_from_narrative(narrative: str) -> str:
    s = narrative.strip().split("\n")[0].strip()
    if len(s) > 80:
        s = s[:77] + "..."
    return s or "Untitled Story"


def heuristic_parse(narrative: str) -> dict[str, Any]:
    sents = _sentences(narrative)
    caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", narrative)
    names = []
    for c in caps:
        if c not in names and c not in {"The", "She", "He", "They", "It", "We", "I"}:
            names.append(c)
    names = names[:8]
    characters = [
        {
            "name": n,
            "role": "protagonist" if i == 0 else "secondary",
            "description": "",
            "relationships": [],
        }
        for i, n in enumerate(names)
    ]
    if not characters:
        characters = [{"name": "Protagonist", "role": "protagonist", "description": "", "relationships": []}]

    ambiguities: list[dict[str, Any]] = []
    low = narrative.lower()
    if "silently" in low or "without a word" in low:
        ambiguities.append(
            {
                "quote": "silent reaction",
                "interpretations": ["grief", "anger", "relief", "shock"],
                "confidence": 0.45,
            }
        )
    if "letter" in low and "cry" in low:
        ambiguities.append(
            {
                "quote": "emotional response to letter",
                "interpretations": ["loss", "betrayal", "joy", "fear"],
                "confidence": 0.5,
            }
        )

    genre = "drama"
    if any(w in low for w in ("hacker", "cyber", "neon", "tower", "security")):
        genre = "cyberpunk action"
    elif any(w in low for w in ("astronaut", "radio", "observatory", "space")):
        genre = "melancholic science fiction"

    return {
        "title": _title_from_narrative(narrative),
        "genre": genre,
        "characters": characters,
        "locations": [{"name": "Primary location", "description": "Inferred from narrative tone"}],
        "timeline": [{"label": "Main arc", "summary": " ".join(sents[:3]) if sents else narrative[:200]}],
        "events": [{"summary": s} for s in sents[:12]],
        "emotional_arcs": [{"character": characters[0]["name"], "arc": "rising tension to resolution"}],
        "conflicts": [{"summary": "Central narrative tension"}],
        "themes": ["identity", "consequence"],
        "ambiguities": ambiguities,
    }


def heuristic_plan_scenes(narrative: str, parsed: dict[str, Any], seed: int) -> list[dict[str, Any]]:
    paras = [p.strip() for p in narrative.split("\n\n") if p.strip()]
    chunks = paras if len(paras) >= 2 else _sentences(narrative)
    if len(chunks) < 3:
        text = narrative.strip()
        n = max(3, min(6, len(text) // 400 + 3))
        step = max(1, len(text) // n)
        chunks = [text[i : i + step] for i in range(0, len(text), step)][:n]
    scenes = []
    transitions = ["cut", "dissolve", "cut", "fade", "dissolve", "cut"]
    for i, chunk in enumerate(chunks[:8]):
        sid = f"scene_{i+1:02d}"
        scenes.append(
            {
                "scene_id": sid,
                "scene_title": f"{parsed.get('title', 'Scene')} — Part {i+1}",
                "location": parsed["locations"][0]["name"] if parsed.get("locations") else "Unspecified",
                "time_of_day": ["day", "night", "dusk", "dawn"][ (seed + i) % 4],
                "characters_present": [c["name"] for c in parsed.get("characters", [])][:4],
                "scene_goal": chunk[:240] + ("…" if len(chunk) > 240 else ""),
                "emotional_tone": ["melancholy", "tension", "hope", "dread", "awe", "resolve"][ (seed // 7 + i) % 6],
                "transition_type": transitions[i % len(transitions)],
                "duration_estimate": f"{45 + (i * 15)}s",
                "visual_priority": "high" if i in {0, len(chunks) - 1} else "medium",
                "body_text": chunk,
            }
        )
    return scenes


def director_preset(i: int, emotional_tone: str) -> dict[str, Any]:
    angles = ["wide", "medium", "close_up", "over_shoulder", "low_angle", "high_angle"]
    shots = ["establishing", "two_shot", "insert", "tracking", "static", "handheld"]
    palettes = [
        "desaturated blues",
        "teal and orange",
        "monochrome with red accent",
        "warm amber",
        "cold steel",
        "neon magenta and cyan",
    ]
    return {
        "camera_angle": angles[i % len(angles)],
        "shot_type": shots[i % len(shots)],
        "lighting": "low contrast, soft fill" if "melanch" in emotional_tone else "high contrast, rim light",
        "color_palette": palettes[i % len(palettes)],
        "mood": emotional_tone,
        "cinematic_style": "intimate realism" if i % 2 == 0 else "stylized genre cinema",
        "pacing": "slow" if i % 3 == 0 else "moderate",
    }

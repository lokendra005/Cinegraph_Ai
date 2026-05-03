from __future__ import annotations

from typing import Any


def run_evaluator(
    narrative: str,
    parsed: dict[str, Any],
    scenes: list[dict[str, Any]],
    continuity: dict[str, Any],
) -> dict[str, Any]:
    n_scenes = len(scenes)
    narrative_alignment = 0.75 + min(0.2, n_scenes * 0.02)
    if len(narrative) > 200:
        narrative_alignment += 0.03
    cont_score = 0.9
    if continuity.get("violations"):
        cont_score = max(0.55, 0.9 - 0.07 * len(continuity["violations"]))
    visual = 0.82
    amb_score = 0.85 if parsed.get("ambiguities") else 0.92
    overall = round((narrative_alignment + cont_score + visual + amb_score) / 4, 3)
    return {
        "narrative_alignment_score": round(min(0.98, narrative_alignment), 3),
        "continuity_score": round(cont_score, 3),
        "visual_consistency_score": visual,
        "ambiguity_handling_score": round(amb_score, 3),
        "notes": "Heuristic evaluator for MVP; replace with LLM-as-judge or human rubric for production.",
        "continuity_violations": continuity.get("violations", []),
    }

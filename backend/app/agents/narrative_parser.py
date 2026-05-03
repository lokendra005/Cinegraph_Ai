from __future__ import annotations

from typing import Any

from app.agents.heuristic import heuristic_parse
from app.services.llm import call_claude_json

PARSE_SYSTEM = """You are the Narrative Parser for CineGraph AI. Return ONLY valid JSON with keys:
title, genre, characters, locations, timeline, events, emotional_arcs, conflicts, themes, ambiguities.
characters: array of {name, role, description, relationships: [{with, relation}]}.
locations: array of {name, description}.
timeline: array of {label, summary}.
events: array of {summary}.
emotional_arcs: array of {character, arc}.
conflicts: array of {summary}.
themes: array of strings.
ambiguities: array of {quote, interpretations: string array, confidence: number between 0 and 1}.
Infer reasonably from the narrative; use empty arrays only when truly absent."""


def run_parser(narrative: str, use_llm: bool) -> dict[str, Any]:
    if use_llm:
        try:
            return call_claude_json(
                PARSE_SYSTEM,
                f"Narrative:\n{narrative}",
            )
        except Exception:
            pass
    return heuristic_parse(narrative)

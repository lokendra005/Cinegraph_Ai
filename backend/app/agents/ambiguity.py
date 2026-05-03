from __future__ import annotations

import json
from typing import Any

from app.services.llm import call_claude_json

AMB_SYSTEM = """You resolve narrative ambiguities. Return ONLY JSON:
{"resolutions": [{"quote": string, "chosen_interpretation": string, "rationale": string, "confidence": number}]}
Match each ambiguity quote from input when possible. If none, return empty resolutions."""


def run_ambiguity(parsed: dict[str, Any], use_llm: bool) -> list[dict[str, Any]]:
    amb = parsed.get("ambiguities") or []
    if not amb:
        return []
    if use_llm:
        try:
            out = call_claude_json(AMB_SYSTEM, json.dumps(amb)[:8000])
            res = out.get("resolutions") or []
            if isinstance(res, list):
                return res
        except Exception:
            pass
    resolutions = []
    for a in amb:
        interp = (a.get("interpretations") or ["unspecified"])[0]
        resolutions.append(
            {
                "quote": a.get("quote", ""),
                "chosen_interpretation": interp,
                "rationale": "Heuristic default: first plausible interpretation for offline demo.",
                "confidence": float(a.get("confidence") or 0.4),
            }
        )
    return resolutions

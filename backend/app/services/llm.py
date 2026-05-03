from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import get_settings


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return json.loads(m.group(1).strip())
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Could not parse JSON from model response")


def _call_anthropic_json(system: str, user: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=8192,
        temperature=settings.llm_temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = msg.content[0].text
    return _extract_json(text)


def _call_groq_json(system: str, user: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    payload = {
        "model": settings.groq_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": settings.llm_temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=45.0) as client:
        res = client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        res.raise_for_status()
        data = res.json()
    content = data["choices"][0]["message"]["content"]
    return _extract_json(content)


def call_claude_json(system: str, user: str) -> dict[str, Any]:
    """
    Backward-compatible function name used by agents.
    Routes to provider configured in settings.
    """
    settings = get_settings()
    provider = (settings.llm_provider or "auto").strip().lower()

    if provider == "anthropic":
        return _call_anthropic_json(system, user)
    if provider == "groq":
        return _call_groq_json(system, user)
    if provider == "auto":
        if settings.anthropic_api_key:
            return _call_anthropic_json(system, user)
        if settings.groq_api_key:
            return _call_groq_json(system, user)
        raise RuntimeError("No configured LLM provider key found")
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

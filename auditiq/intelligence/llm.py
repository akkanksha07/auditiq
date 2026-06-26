"""Thin wrapper around the Anthropic client (extraction, findings, news)."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Optional

from ..config import settings


class LLMError(RuntimeError):
    """Raised when the LLM is unavailable or misconfigured."""


@lru_cache(maxsize=1)
def get_client():
    if not settings.has_api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set — add it to your .env to enable AI features.")
    from anthropic import Anthropic

    return Anthropic(api_key=settings.anthropic_api_key)


def _text_from(resp) -> str:
    return "\n".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()


def complete(
    prompt: str,
    *,
    model: Optional[str] = None,
    max_tokens: int = 1500,
    system: Optional[str] = None,
    tools: Optional[list] = None,
    temperature: float = 0.0,
) -> str:
    """Run a single-turn completion and return the assembled text content."""
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": model or settings.extraction_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    return _text_from(client.messages.create(**kwargs))


def extract_json(text: str) -> Any:
    """Parse a JSON value from a model response, tolerating fences / prose."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise

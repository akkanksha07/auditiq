"""News sentiment & risk cross-referencing via Claude + web search."""
from __future__ import annotations

from typing import Optional

from ..config import settings
from ..models import NewsArticle, NewsSentiment
from .llm import complete, extract_json

# Anthropic server-side web-search tool (requires web search enabled on the account).
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


def _prompt(company: str) -> str:
    return f"""Research recent news (roughly the last 12 months) about "{company}", focusing on
financial health, accounting or governance issues, regulatory actions, litigation,
management/auditor changes, and any fraud or audit concerns.

Use web search, then return ONLY a JSON object (no markdown, no backticks):
{{
  "score": number,            // overall sentiment, -1.0 (very negative) to 1.0 (very positive)
  "label": "Positive|Neutral|Negative",
  "summary": string,          // 2-3 sentences focused on audit / financial risk
  "flags": [string, ...],     // specific governance / fraud / financial-risk signals (may be empty)
  "articles": [
    {{"title": string, "source": string, "date": "YYYY-MM-DD", "url": string,
      "sentiment": "positive|neutral|negative"}}
  ]
}}
Include up to 6 of the most relevant articles with working URLs."""


def get_news_sentiment(company_name: str, model: Optional[str] = None) -> Optional[NewsSentiment]:
    """Return news sentiment, or None if disabled (no key) or the call fails."""
    if not company_name or not settings.has_api_key:
        return None
    try:
        raw = complete(
            _prompt(company_name),
            model=model or settings.news_model,
            max_tokens=2500,
            tools=[WEB_SEARCH_TOOL],
        )
        data = extract_json(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    articles: list[NewsArticle] = []
    for a in data.get("articles", []) or []:
        if isinstance(a, dict):
            try:
                articles.append(NewsArticle.model_validate(a))
            except Exception:
                continue

    try:
        score = float(data.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    label = data.get("label") or (
        "Negative" if score < -0.15 else "Positive" if score > 0.15 else "Neutral"
    )

    return NewsSentiment(
        score=round(score, 2), label=label,
        summary=data.get("summary", "") or "",
        flags=[f for f in (data.get("flags") or []) if isinstance(f, str)],
        articles=articles,
    )

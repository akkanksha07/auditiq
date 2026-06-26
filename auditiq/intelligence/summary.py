"""Claude-written plain-English audit risk summary."""
from __future__ import annotations

from typing import Optional

from ..config import settings
from ..models import YearAnalysis
from .llm import complete


def generate_summary(year: YearAnalysis, industry: str, model: Optional[str] = None) -> str:
    """Return a short senior-auditor summary, or '' if AI is unavailable/fails."""
    if not settings.has_api_key:
        return ""

    b = year.beneish
    a = year.altman
    flagged = "; ".join(
        f"{r.label}: {r.company}{r.unit} vs {r.industry}{r.unit}"
        for r in year.benchmarks if r.flag != "ok"
    ) or "none significant"

    prompt = f"""You are a senior auditor at a Big 4 firm writing a concise risk summary for a junior colleague.

Company: {year.financials.company_name} ({year.year})
Industry: {industry}
Beneish M-Score: {b.m_score if b else 'n/a'} ({'MANIPULATOR ZONE (> -1.78)' if b and b.is_manipulator else 'non-manipulator zone'})
Altman Z-Score: {a.z_score if a else 'n/a'} ({a.zone_label if a else 'n/a'})
Key benchmark deviations: {flagged}
Textual red flags: {'; '.join(year.financials.red_flags) or 'none'}
Analyst notes: {year.financials.notes or 'none'}

Write a 3-4 sentence plain-English summary as a senior auditor would. Be direct and
analytical and mention the most important risk first. No bullet points. Do not start
with "This company"."""

    try:
        return complete(prompt, model=model or settings.narrative_model, max_tokens=400)
    except Exception:
        return ""

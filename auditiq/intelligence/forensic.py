"""Qualitative forensic review — Claude reads the report's own disclosures.

This is the layer forensic accountants actually start from: the independent
auditor's report, key/critical audit matters, the notes, and management's
discussion. We locate those sections heuristically, hand focused excerpts to
Claude, and require a VERBATIM evidence quote for every flag so a human can
verify each one against the source. Unsupported categories must be omitted —
an empty result is a valid result.
"""
from __future__ import annotations

import re
from typing import Optional

from ..config import settings
from ..models import DisclosureFlag, ForensicReview
from .llm import complete, extract_json

CATEGORIES: dict[str, str] = {
    "going_concern": "Going-concern language or material uncertainty",
    "restatement": "Restatement or correction of prior-period figures",
    "icfr_weakness": "Material weakness or significant deficiency in internal controls",
    "auditor_change": "Change of external auditor, auditor dispute, or unusual tenure signals",
    "management_change": "CFO / CEO / senior finance-management departures",
    "related_party": "Related-party transactions",
    "revenue_recognition": "Changes to, or unusually aggressive, revenue-recognition policy",
    "non_gaap": "Heavy reliance on non-GAAP / adjusted / alternative performance measures",
    "other": "Other disclosure a forensic accountant would investigate",
}

CATEGORY_LABEL: dict[str, str] = {
    "going_concern": "Going concern",
    "restatement": "Restatement",
    "icfr_weakness": "Internal controls",
    "auditor_change": "Auditor change",
    "management_change": "Management change",
    "related_party": "Related parties",
    "revenue_recognition": "Revenue recognition",
    "non_gaap": "Non-GAAP reliance",
    "other": "Other",
}

# (pattern, human label) — headings/phrases that mark forensically relevant sections.
_SECTIONS: list[tuple[str, str]] = [
    (r"independent auditor", "Independent auditor's report"),
    (r"key audit matter", "Key audit matters"),
    (r"critical audit matter", "Critical audit matters"),
    (r"going concern", "Going concern"),
    (r"material uncertainty", "Material uncertainty"),
    (r"material weakness", "Material weakness"),
    (r"internal control", "Internal controls"),
    (r"restat(?:ement|ed|e)", "Restatements"),
    (r"related part(?:y|ies)", "Related parties"),
    (r"revenue recognition", "Revenue recognition"),
    (r"critical accounting", "Critical accounting policies"),
    (r"alternative performance", "Alternative performance measures"),
    (r"non-?gaap|non-?ifrs", "Non-GAAP measures"),
    (r"management'?s discussion", "Management's discussion & analysis"),
    (r"strategic report", "Strategic report"),
    (r"audit committee", "Audit committee report"),
]

_MAX_HITS_PER_SECTION = 2
_WINDOW_AFTER = 2400
_WINDOW_BEFORE = 400
_BUDGET = 48_000


def _locate_sections(text: str) -> tuple[str, list[str]]:
    """Focused windows around forensic headings, merged, within a char budget."""
    low = text.lower()
    spans: list[tuple[int, int]] = []
    found: list[str] = []
    for pattern, label in _SECTIONS:
        hits = 0
        for m in re.finditer(pattern, low):
            spans.append((max(0, m.start() - _WINDOW_BEFORE),
                          min(len(text), m.end() + _WINDOW_AFTER)))
            hits += 1
            if hits >= _MAX_HITS_PER_SECTION:
                break
        if hits:
            found.append(label)

    if not spans:
        return text[:_BUDGET], []

    spans.sort()
    merged: list[list[int]] = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    parts: list[str] = []
    used = 0
    for s, e in merged:
        chunk = text[s:e]
        if used + len(chunk) > _BUDGET:
            chunk = chunk[: max(0, _BUDGET - used)]
        if chunk:
            parts.append(chunk)
            used += len(chunk)
        if used >= _BUDGET:
            break
    return "\n\n[…]\n\n".join(parts), found


def _prompt(company: str, bundle: str, sections: list[str]) -> str:
    cats = "\n".join(f"- {k}: {v}" for k, v in CATEGORIES.items())
    located = ", ".join(sections) if sections else "no named sections located — full text excerpt"
    return f"""You are a forensic accountant reviewing excerpts from the annual report of {company}.
The excerpts were gathered from around these sections: {located}.

Identify disclosure-level red flags ONLY where the text explicitly supports them, in these categories:
{cats}

Rules — follow strictly:
- Report a category ONLY if the provided text clearly supports it. Never infer, assume, or speculate.
- Every flag MUST include a SHORT VERBATIM QUOTE (max 300 characters) copied exactly from the text as evidence. If you cannot quote it, do not report it.
- Routine boilerplate is NOT a flag (e.g. a standard going-concern assessment that concludes no material uncertainty, or ordinary intercompany disclosures).
- Severity: high = auditor-level warnings (going-concern uncertainty, material weakness, restatement); medium = notable but common (related parties, policy changes, heavy non-GAAP); low = worth a look.
- An empty flags list is a perfectly good answer for a clean report.

Return ONLY JSON, no markdown:
{{
  "summary": "2-3 sentence overall read of the disclosures, appropriately hedged",
  "flags": [
    {{
      "category": "going_concern|restatement|icfr_weakness|auditor_change|management_change|related_party|revenue_recognition|non_gaap|other",
      "severity": "low|medium|high",
      "title": "one line",
      "detail": "what the report says, in plain English",
      "evidence": "verbatim quote from the text",
      "location": "section name or page if identifiable, else null",
      "why": "why a forensic accountant cares (1-2 sentences)",
      "innocent": ["1-3 common benign explanations"]
    }}
  ]
}}

Report excerpts:
{bundle}"""


def parse_review(data, sections: Optional[list[str]] = None) -> Optional[ForensicReview]:
    """Validate/normalise the model's JSON into a ForensicReview (pure; testable)."""
    if not isinstance(data, dict):
        return None
    flags: list[DisclosureFlag] = []
    for f in data.get("flags") or []:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity", "medium")).lower()
        f["severity"] = sev if sev in ("low", "medium", "high") else "medium"
        if f.get("category") not in CATEGORIES:
            f["category"] = "other"
        if isinstance(f.get("innocent"), str):
            f["innocent"] = [f["innocent"]]
        try:
            flags.append(DisclosureFlag.model_validate(f))
        except Exception:
            continue
    order = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda x: order.get(x.severity, 1))
    return ForensicReview(
        flags=flags,
        summary=str(data.get("summary") or ""),
        sections_reviewed=list(sections or []),
    )


def analyze_disclosures(
    text: str, company_name: Optional[str] = None, model: Optional[str] = None,
) -> Optional[ForensicReview]:
    """Run the disclosure review. Returns None without a key / on failure."""
    if not text or not settings.has_api_key:
        return None
    bundle, sections = _locate_sections(text)
    try:
        raw = complete(
            _prompt(company_name or "the company", bundle, sections),
            model=model or settings.forensic_model, max_tokens=3000,
        )
        data = extract_json(raw)
    except Exception:
        return None
    return parse_review(data, sections)

"""Tier-weighted synthesis of flags by forensic signal strength.

The headline must reflect *how forensically meaningful* the flags are, not their
raw count — otherwise a legitimate statistical outlier (a very healthy company)
out-flags a real manipulator whose fraud never touched the reported ratios.

  Tier 1 — earnings quality & distress   (Beneish, Altman): real predictive signal.
  Tier 2 — disclosures                    (textual flags, DisclosureFlags).
  Tier 3 — outlier vs peers               (benchmarks, Benford): CONTEXT ONLY.

Only Tier 1 + Tier 2 drive the headline; Tier 3 is reported separately and never
counts as a red flag. This module adds no new calculation — it re-weights the
findings the engines already produced.
"""
from __future__ import annotations

from typing import Optional

from ..models import DisclosureFlag, Finding, RiskLevel, TieredAssessment

CATEGORY_TIER: dict[str, int] = {
    "beneish": 1, "altman": 1,      # earnings quality & distress
    "textual": 2,                   # qualitative / disclosure
    "benford": 3, "benchmark": 3,   # outlier vs peers — context only
    "clear": 0,                     # the "all clear" finding counts for nothing
}
TIER_LABEL = {1: "Earnings quality & distress", 2: "Disclosures", 3: "Peer context"}


def finding_tier(category: str) -> int:
    return CATEGORY_TIER.get(category, 3)


def assess_tiers(findings: list[Finding],
                 disclosure_flags: Optional[list[DisclosureFlag]] = None) -> TieredAssessment:
    disclosure_flags = disclosure_flags or []
    t1 = [f for f in findings if f.tier == 1]
    t2f = [f for f in findings if f.tier == 2]
    t3 = [f for f in findings if f.tier == 3]

    # Headline severity comes ONLY from Tier 1 + Tier 2 (disclosure severities included).
    levels = [f.level for f in t1] + [f.level for f in t2f] + [d.severity for d in disclosure_flags]
    level: RiskLevel = ("high" if "high" in levels
                        else "medium" if "medium" in levels else "low")

    substantive = t1 + t2f
    top = ([f.title for f in substantive if f.level == "high"]
           + [d.title for d in disclosure_flags if d.severity == "high"])
    if not top:
        top = [f.title for f in substantive] + [d.title for d in disclosure_flags]

    return TieredAssessment(
        level=level,
        substantive=len(t1) + len(t2f) + len(disclosure_flags),
        context=len(t3),
        t1=len(t1), t2=len(t2f) + len(disclosure_flags), t3=len(t3),
        top=top[:3],
    )

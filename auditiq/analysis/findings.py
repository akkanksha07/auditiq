"""Rules-based synthesis of red flags from every analysis engine into Findings.

Framing matters: every finding is a red flag *warranting investigation*, never a
verdict. Each carries a plain-English ``why`` (what specifically tripped the
screen) and ``innocent`` (the benign explanations to rule out first), supplied
by :mod:`auditiq.analysis.explanations`. The flag logic and thresholds are
unchanged — only the explanatory content is new.
"""
from __future__ import annotations

from typing import Optional

from ..models import (
    AltmanResult, BenchmarkRow, BeneishResult, BenfordResult,
    Finding, FinancialStatement, RiskLevel,
)
from . import explanations as ex
from .beneish import elevated_components


def _fmt(v: Optional[float]) -> str:
    return "N/A" if v is None else f"{v:g}"


def build_findings(
    financials: FinancialStatement,
    beneish: Optional[BeneishResult],
    altman: Optional[AltmanResult],
    benford: Optional[BenfordResult],
    benchmarks: list[BenchmarkRow],
) -> list[Finding]:
    findings: list[Finding] = []

    # ── Beneish ──────────────────────────────────────────────────────────────
    if beneish and beneish.is_manipulator:
        drivers = elevated_components(beneish) or ["multiple indicators"]
        why, innocent = ex.beneish_explanation(drivers)
        findings.append(Finding(
            level="high", category="beneish",
            title="Earnings-manipulation screen flagged",
            body=(f"Beneish M-Score of {beneish.m_score} is above the {beneish.threshold} "
                  f"screening threshold (probit score {beneish.probability}%). "
                  f"Largest contributors: {', '.join(drivers)}. Warrants investigation."),
            why=why, innocent=innocent,
        ))

    # ── Altman ───────────────────────────────────────────────────────────────
    if altman and altman.zone == "high":
        why, innocent = ex.altman_explanation("high", altman.model_used)
        findings.append(Finding(
            level="high", category="altman",
            title="Solvency screen: distress zone",
            body=(f"Altman Z-Score ({altman.model_used}) of {altman.z_score} falls in the "
                  f"distress band — investigate going-concern indicators."),
            why=why, innocent=innocent,
        ))
    elif altman and altman.zone == "medium":
        why, innocent = ex.altman_explanation("medium", altman.model_used)
        findings.append(Finding(
            level="medium", category="altman",
            title="Solvency screen: grey zone",
            body=(f"Altman Z-Score of {altman.z_score} sits in the grey band; "
                  f"monitor solvency."),
            why=why, innocent=innocent,
        ))

    # ── Benford ──────────────────────────────────────────────────────────────
    if benford and benford.suspicious:
        why, innocent = ex.benford_explanation(benford.mad, benford.n)
        findings.append(Finding(
            level="medium", category="benford",
            title="Benford screen: digit-distribution deviation",
            body=(f"The leading digits of {benford.n} figures show {benford.conformity} with "
                  f"Benford's expected curve (MAD {benford.mad}, p={benford.p_value}). "
                  f"A deviation is a prompt to examine the numeric population — not evidence "
                  f"of manipulation on its own."),
            why=why, innocent=innocent,
        ))

    # ── Benchmarks (high then medium) ────────────────────────────────────────
    for b in benchmarks:
        if b.flag == "high":
            why, innocent = ex.benchmark_explanation(b)
            findings.append(Finding(
                level="high", category="benchmark",
                title=f"{b.label} significantly off industry",
                body=(f"Company {b.label} is {_fmt(b.company)}{b.unit} versus an industry "
                      f"average of {b.industry}{b.unit}. Warrants investigation."),
                why=why, innocent=innocent,
            ))
    for b in benchmarks:
        if b.flag == "medium":
            why, innocent = ex.benchmark_explanation(b)
            findings.append(Finding(
                level="medium", category="benchmark",
                title=f"{b.label} off sector average",
                body=(f"{b.label} of {_fmt(b.company)}{b.unit} versus benchmark "
                      f"{b.industry}{b.unit}. Monitor for further deterioration."),
                why=why, innocent=innocent,
            ))

    # ── Textual red flags from the report ────────────────────────────────────
    for flag in (financials.red_flags or [])[:4]:
        why, innocent = ex.textual_explanation()
        findings.append(Finding(
            level="medium", category="textual",
            title="Red flag in the report's own text", body=flag,
            why=why, innocent=innocent,
        ))

    if not findings:
        findings.append(Finding(
            level="low", category="clear",
            title="No screening flags raised",
            body=("No screening thresholds were breached and no benchmark deviation was "
                  "material. Routine procedures recommended — a clean screen is not a "
                  "guarantee of clean accounts."),
            why="All quantitative screens returned values inside their normal ranges.",
        ))

    return findings


def overall_risk(findings: list[Finding]) -> RiskLevel:
    if any(f.level == "high" for f in findings):
        return "high"
    if any(f.level == "medium" for f in findings):
        return "medium"
    return "low"

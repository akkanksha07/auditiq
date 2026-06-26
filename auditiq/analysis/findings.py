"""Rules-based synthesis of red flags from every analysis engine into Findings."""
from __future__ import annotations

from typing import Optional

from ..models import (
    AltmanResult, BenchmarkRow, BeneishResult, BenfordResult,
    Finding, FinancialStatement, RiskLevel,
)
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
        findings.append(Finding(
            level="high", category="beneish", icon="🚨",
            title="Earnings manipulation likely",
            body=(f"Beneish M-Score of {beneish.m_score} exceeds the {beneish.threshold} "
                  f"manipulator threshold (probit-implied probability {beneish.probability}%). "
                  f"Key drivers: {', '.join(drivers)}."),
        ))

    # ── Altman ───────────────────────────────────────────────────────────────
    if altman and altman.zone == "high":
        findings.append(Finding(
            level="high", category="altman", icon="📉",
            title="Elevated bankruptcy risk",
            body=(f"Altman Z-Score ({altman.model_used}) of {altman.z_score} falls in the "
                  f"distress zone — material going-concern risk."),
        ))
    elif altman and altman.zone == "medium":
        findings.append(Finding(
            level="medium", category="altman", icon="📉",
            title="Bankruptcy risk in grey zone",
            body=(f"Altman Z-Score of {altman.z_score} sits in the grey zone; "
                  f"solvency warrants monitoring."),
        ))

    # ── Benford ──────────────────────────────────────────────────────────────
    if benford and benford.suspicious:
        findings.append(Finding(
            level="medium", category="benford", icon="🔢",
            title="Digit-distribution anomaly",
            body=(f"Benford's Law analysis on {benford.n} figures shows {benford.conformity} "
                  f"(MAD {benford.mad}, p={benford.p_value}). May indicate rounding, "
                  f"estimation, or fabricated numbers."),
        ))

    # ── Benchmarks (high then medium) ────────────────────────────────────────
    for b in benchmarks:
        if b.flag == "high":
            findings.append(Finding(
                level="high", category="benchmark", icon="⚠️",
                title=f"{b.label} significantly off industry",
                body=(f"Company {b.label} is {_fmt(b.company)}{b.unit} versus an industry "
                      f"average of {b.industry}{b.unit}. Warrants investigation."),
            ))
    for b in benchmarks:
        if b.flag == "medium":
            findings.append(Finding(
                level="medium", category="benchmark", icon="📌",
                title=f"{b.label} off sector average",
                body=(f"{b.label} of {_fmt(b.company)}{b.unit} versus benchmark "
                      f"{b.industry}{b.unit}. Monitor for further deterioration."),
            ))

    # ── Textual red flags from the report ────────────────────────────────────
    for flag in (financials.red_flags or [])[:4]:
        findings.append(Finding(
            level="medium", category="textual", icon="📄",
            title="Textual red flag in report", body=flag,
        ))

    if not findings:
        findings.append(Finding(
            level="low", category="clear", icon="✅",
            title="No major red flags detected",
            body=("Key ratios are within acceptable ranges and the fraud / bankruptcy "
                  "indicators are benign. Routine audit procedures recommended."),
        ))

    return findings


def overall_risk(findings: list[Finding]) -> RiskLevel:
    if any(f.level == "high" for f in findings):
        return "high"
    if any(f.level == "medium" for f in findings):
        return "medium"
    return "low"

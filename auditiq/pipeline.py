"""High-level orchestration: extracted statements -> per-year analysis -> AuditReport.

This module is intentionally free of network/LLM calls so it can be unit-tested
offline. AI-derived inputs (news, narrative summary) are passed in by the caller.
"""
from __future__ import annotations

from typing import Optional

from .analysis import altman as altman_mod
from .analysis import benford as benford_mod
from .analysis import beneish as beneish_mod
from .analysis.benchmark import benchmark_ratios
from .analysis.comparison import build_comparison
from .analysis.findings import build_findings, overall_risk
from .analysis.ratios import compute_ratios
from .models import (
    AuditReport, FinancialStatement, NewsSentiment, YearAnalysis,
)


def analyze_year(
    financials: FinancialStatement,
    *,
    industry: str,
    prior: Optional[FinancialStatement] = None,
    benford_text: Optional[str] = None,
) -> YearAnalysis:
    ratios = compute_ratios(financials, prior)
    benchmarks = benchmark_ratios(ratios, industry)
    beneish = beneish_mod.compute_beneish(financials, prior)
    altman = altman_mod.compute_altman(financials, industry=industry)
    benford = benford_mod.analyze_text(benford_text) if benford_text else None
    findings = build_findings(financials, beneish, altman, benford, benchmarks)
    return YearAnalysis(
        year=financials.year or "—", financials=financials, ratios=ratios,
        benchmarks=benchmarks, beneish=beneish, altman=altman,
        benford=benford, findings=findings,
    )


def build_report(
    statements: list[FinancialStatement],
    *,
    industry: str,
    benford_texts: Optional[dict[str, str]] = None,
    news: Optional[NewsSentiment] = None,
    summary: str = "",
) -> AuditReport:
    """Assemble a full report from 1–3 statements (chronological order handled here)."""
    ordered = sorted(statements, key=lambda s: s.year or "")
    benford_texts = benford_texts or {}

    years: list[YearAnalysis] = []
    prior: Optional[FinancialStatement] = None
    for s in ordered:
        years.append(analyze_year(
            s, industry=industry, prior=prior,
            benford_text=benford_texts.get(s.year or ""),
        ))
        prior = s

    risk = "low"
    for ya in years:
        r = overall_risk(ya.findings)
        if r == "high":
            risk = "high"
        elif r == "medium" and risk != "high":
            risk = "medium"

    company = next((s.company_name for s in ordered if s.company_name), "Company")
    return AuditReport(
        company_name=company or "Company", industry=industry, years=years,
        comparison=build_comparison(years), news=news, summary=summary, overall_risk=risk,
    )

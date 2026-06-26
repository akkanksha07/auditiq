"""Multi-year comparison: build trend series and assess direction of travel."""
from __future__ import annotations

from typing import Optional

from ..models import Comparison, TrendPoint, YearAnalysis


def _trend(first: Optional[float], last: Optional[float], tol: float) -> int:
    """+1 if rising beyond tol, -1 if falling beyond tol, else 0."""
    if first is None or last is None:
        return 0
    if last > first + tol:
        return 1
    if last < first - tol:
        return -1
    return 0


def build_comparison(years: list[YearAnalysis]) -> Optional[Comparison]:
    """Compare 2–3 years. Returns None if fewer than two years are available."""
    if len(years) < 2:
        return None

    ordered = sorted(years, key=lambda y: y.year)
    points = [
        TrendPoint(
            year=ya.year,
            revenue=ya.financials.revenue,
            net_income=ya.financials.net_income,
            m_score=ya.beneish.m_score if ya.beneish else None,
            z_score=ya.altman.z_score if ya.altman else None,
            gross_margin=ya.ratios.gross_margin,
        )
        for ya in ordered
    ]
    first, last = points[0], points[-1]

    worse = better = 0
    notes: list[str] = []

    m = _trend(first.m_score, last.m_score, 0.20)  # rising M-Score = worse
    if m > 0:
        worse += 1
        notes.append(f"Beneish M-Score rose from {first.m_score} to {last.m_score} (more manipulation risk).")
    elif m < 0:
        better += 1
        notes.append(f"Beneish M-Score fell from {first.m_score} to {last.m_score} (less manipulation risk).")

    z = _trend(first.z_score, last.z_score, 0.30)  # falling Z = worse
    if z < 0:
        worse += 1
        notes.append(f"Altman Z-Score declined from {first.z_score} to {last.z_score} (weaker solvency).")
    elif z > 0:
        better += 1
        notes.append(f"Altman Z-Score improved from {first.z_score} to {last.z_score} (stronger solvency).")

    gm = _trend(first.gross_margin, last.gross_margin, 0.02)  # falling margin = worse
    if gm < 0:
        worse += 1
        notes.append("Gross margin compressed over the period.")
    elif gm > 0:
        better += 1
        notes.append("Gross margin expanded over the period.")

    ni = _trend(first.net_income, last.net_income, abs((first.net_income or 0)) * 0.05 or 1)
    if ni < 0:
        worse += 1
        notes.append("Net income declined over the period.")

    direction = "worsening" if worse > better else "improving" if better > worse else "stable"
    return Comparison(points=points, direction=direction, notes=notes)

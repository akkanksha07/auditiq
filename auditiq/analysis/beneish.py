"""Beneish M-Score — eight-factor earnings-manipulation model (Beneish, 1999).

    M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
            + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI

An M-Score above -1.78 places the firm in the "manipulator" zone. The model is a
probit, so the implied probability of manipulation is Phi(M). Requires two
consecutive years (current vs prior).
"""
from __future__ import annotations

from typing import Optional

from scipy.stats import norm

from ..config import BENEISH_THRESHOLD
from ..models import BeneishResult, FinancialStatement

# name, plain-English tip, "elevated" threshold (used by the UI/report)
COMPONENT_INFO: dict[str, tuple[str, str, float]] = {
    "DSRI": ("Days Sales in Receivables", "Receivables growing faster than revenue → revenue-inflation risk", 1.1),
    "GMI": ("Gross Margin Index", "Deteriorating margins create pressure to manipulate", 1.1),
    "AQI": ("Asset Quality Index", "Rising intangibles / deferred costs signal risk", 1.0),
    "SGI": ("Sales Growth Index", "High-growth firms have more incentive to manipulate", 1.2),
    "DEPI": ("Depreciation Index", "Slowing depreciation can inflate earnings", 1.0),
    "SGAI": ("SG&A Expense Index", "Rising admin costs relative to revenue", 1.1),
    "TATA": ("Total Accruals / Assets", "High accruals vs cash = earnings-quality concern", 0.08),
    "LVGI": ("Leverage Index", "Rising leverage increases fraud incentive", 1.0),
}


def _safe_div(num: Optional[float], den: Optional[float], default: float = 1.0) -> float:
    if num is None or den is None or den == 0:
        return default
    return num / den


def _add(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else a + b


def _noncurrent_soft_assets(s: FinancialStatement) -> Optional[float]:
    """Assets other than current assets and PP&E (goodwill, intangibles, …)."""
    if s.total_assets is None or s.current_assets is None or s.ppe is None:
        return None
    return s.total_assets - s.current_assets - s.ppe


def _accruals(s: FinancialStatement) -> Optional[float]:
    if s.net_income is None or s.operating_cash_flow is None:
        return None
    return s.net_income - s.operating_cash_flow


def compute_beneish(
    current: FinancialStatement,
    prior: Optional[FinancialStatement],
    threshold: float = BENEISH_THRESHOLD,
) -> Optional[BeneishResult]:
    """Return the M-Score result, or None when no prior year is available."""
    if prior is None:
        return None
    c, p = current, prior

    dsri = _safe_div(_safe_div(c.receivables, c.revenue), _safe_div(p.receivables, p.revenue))

    prev_gm = _safe_div(p.resolved_gross_profit, p.revenue)
    curr_gm = _safe_div(c.resolved_gross_profit, c.revenue)
    gmi = _safe_div(prev_gm, curr_gm)

    curr_aq = _safe_div(_noncurrent_soft_assets(c), c.total_assets)
    prev_aq = _safe_div(_noncurrent_soft_assets(p), p.total_assets)
    aqi = _safe_div(curr_aq, prev_aq)

    sgi = _safe_div(c.revenue, p.revenue)

    prev_dep = _safe_div(p.depreciation, _add(p.depreciation, p.ppe))
    curr_dep = _safe_div(c.depreciation, _add(c.depreciation, c.ppe))
    depi = _safe_div(prev_dep, curr_dep)

    sgai = _safe_div(_safe_div(c.sga, c.revenue), _safe_div(p.sga, p.revenue))

    # TATA defaults to 0 (neutral) rather than 1 when assets are missing.
    tata = _safe_div(_accruals(c), c.total_assets, default=0.0)

    curr_lev = _safe_div(c.resolved_total_liabilities, c.total_assets)
    prev_lev = _safe_div(p.resolved_total_liabilities, p.total_assets)
    lvgi = _safe_div(curr_lev, prev_lev)

    m = (
        -4.84
        + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
        + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi
    )

    # Beneish is a probit model → P(manipulation) = Phi(M).
    probability = float(norm.cdf(m)) * 100.0

    return BeneishResult(
        m_score=round(m, 3),
        probability=round(probability, 1),
        is_manipulator=m > threshold,
        threshold=threshold,
        components={
            "DSRI": round(dsri, 3), "GMI": round(gmi, 3), "AQI": round(aqi, 3),
            "SGI": round(sgi, 3), "DEPI": round(depi, 3), "SGAI": round(sgai, 3),
            "TATA": round(tata, 3), "LVGI": round(lvgi, 3),
        },
    )


def elevated_components(result: BeneishResult) -> list[str]:
    """Component keys whose value exceeds their 'elevated' threshold."""
    return [k for k, v in result.components.items()
            if k in COMPONENT_INFO and v > COMPONENT_INFO[k][2]]

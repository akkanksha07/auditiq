"""Financial ratio computations from a single statement (+ optional prior year)."""
from __future__ import annotations

from typing import Optional

from ..models import FinancialStatement, RatioSet


def _safe(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _mul(a: Optional[float], b: float) -> Optional[float]:
    return None if a is None else a * b


def _sub(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else a - b


def _round(v: Optional[float], n: int) -> Optional[float]:
    return None if v is None else round(v, n)


def compute_ratios(s: FinancialStatement, prior: Optional[FinancialStatement] = None) -> RatioSet:
    # COGS fallback (≈70% of revenue) keeps inventory-days meaningful when COGS is absent.
    cogs = s.cogs if s.cogs not in (None, 0) else _mul(s.revenue, 0.7)
    prev_rev = prior.revenue if prior else None
    debt = s.total_debt if s.total_debt is not None else s.resolved_total_liabilities

    return RatioSet(
        receivables_days=_round(_safe(_mul(s.receivables, 365), s.revenue), 1),
        inventory_days=_round(_safe(_mul(s.inventory, 365), cogs), 1),
        gross_margin=_round(_safe(s.resolved_gross_profit, s.revenue), 4),
        current_ratio=_round(_safe(s.current_assets, s.current_liabilities), 2),
        debt_to_equity=_round(_safe(debt, s.equity), 2),
        interest_coverage=_round(_safe(s.ebit, s.interest_expense), 2),
        asset_turnover=_round(_safe(s.revenue, s.total_assets), 2),
        revenue_growth=_round(_safe(_sub(s.revenue, prev_rev), prev_rev), 4),
    )

"""Altman Z-Score — bankruptcy-risk model with three published variants.

    original (Z)   public manufacturers:
        1.2 X1 + 1.4 X2 + 3.3 X3 + 0.6 X4 + 0.999 X5
    private (Z')   private firms (book equity in X4):
        0.717 X1 + 0.847 X2 + 3.107 X3 + 0.420 X4 + 0.998 X5
    emerging (Z'') non-manufacturing / emerging markets (no X5):
        6.56 X1 + 3.26 X2 + 6.72 X3 + 1.05 X4 + 3.25

X1 = working capital / total assets   X2 = retained earnings / total assets
X3 = EBIT / total assets              X4 = equity / total liabilities
X5 = sales / total assets
"""
from __future__ import annotations

from typing import Optional

from ..config import ALTMAN_ZONES
from ..models import AltmanResult, FinancialStatement

NON_MANUFACTURING = {"retail", "technology", "financial", "healthcare"}


def _select_model(s: FinancialStatement, model: str, industry: Optional[str] = None) -> str:
    if model != "auto":
        return model
    # Prefer an explicitly supplied industry (e.g. the user's dashboard selection)
    # over the statement's extracted industry, so the whole report stays consistent.
    ind = (industry or s.industry or "").lower()
    if ind in NON_MANUFACTURING:
        return "emerging"
    return "original" if s.market_value_equity is not None else "private"


def compute_altman(
    s: FinancialStatement, model: str = "auto", industry: Optional[str] = None
) -> Optional[AltmanResult]:
    ta = s.total_assets
    tl = s.resolved_total_liabilities
    if not ta or ta == 0 or not tl or tl == 0:
        return None

    model = _select_model(s, model, industry)
    equity = (s.market_value_equity if model == "original" and s.market_value_equity is not None
              else s.equity if s.equity is not None else s.market_value_equity)
    if equity is None:
        return None

    x1 = (s.working_capital / ta) if s.working_capital is not None else 0.0
    x2 = (s.retained_earnings / ta) if s.retained_earnings is not None else 0.0
    x3 = (s.ebit / ta) if s.ebit is not None else 0.0
    x4 = equity / tl
    x5 = (s.revenue / ta) if s.revenue is not None else 0.0

    if model == "original":
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5
        comps = {"X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5}
    elif model == "private":
        z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
        comps = {"X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5}
    else:  # emerging / non-manufacturing (Z'') — no X5, constant +3.25
        z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4 + 3.25
        comps = {"X1": x1, "X2": x2, "X3": x3, "X4": x4}

    zones = ALTMAN_ZONES[model]
    if z >= zones["safe"]:
        zone, label = "low", "Safe"
    elif z <= zones["distress"]:
        zone, label = "high", "Distress"
    else:
        zone, label = "medium", "Grey"

    return AltmanResult(
        model_used=model, z_score=round(z, 2), zone=zone, zone_label=label,
        components={k: round(v, 3) for k, v in comps.items()},
    )

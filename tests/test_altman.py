"""Tests for the Altman Z-Score engine."""
from auditiq.analysis.altman import compute_altman
from auditiq.models import FinancialStatement


def _firm(**over) -> FinancialStatement:
    base = {
        "industry": "manufacturing", "revenue": 1000, "ebit": 150,
        "totalAssets": 1000, "currentAssets": 600, "currentLiabilities": 300,
        "retainedEarnings": 400, "totalLiabilities": 300, "equity": 700,
        "marketValueEquity": 1200,
    }
    base.update(over)
    return FinancialStatement.model_validate(base)


def test_model_auto_selection():
    assert compute_altman(_firm(industry="retail")).model_used == "emerging"
    assert compute_altman(_firm(industry="manufacturing")).model_used == "original"
    # No market value -> private variant for a manufacturer.
    assert compute_altman(_firm(industry="manufacturing", marketValueEquity=None)).model_used == "private"


def test_healthy_firm_is_safe():
    res = compute_altman(_firm())
    assert res is not None
    assert res.zone == "low"
    assert res.zone_label == "Safe"


def test_distressed_firm_is_high_risk():
    distressed = _firm(
        ebit=-200, retainedEarnings=-500, currentAssets=200, currentLiabilities=600,
        totalLiabilities=950, equity=50, marketValueEquity=40,
    )
    res = compute_altman(distressed)
    assert res is not None
    assert res.zone == "high"


def test_missing_data_returns_none():
    assert compute_altman(FinancialStatement.model_validate({"revenue": 100})) is None

"""Tests for the Beneish M-Score engine."""
from auditiq.analysis.beneish import compute_beneish
from auditiq.models import FinancialStatement
from auditiq.sample_data import get_sample_statements


def _clean_year() -> FinancialStatement:
    """A statement where all YoY indices = 1 and accruals = 0 (NI == OCF)."""
    return FinancialStatement.model_validate({
        "revenue": 1000, "cogs": 600, "receivables": 100, "totalAssets": 2000,
        "currentAssets": 500, "ppe": 800, "depreciation": 100, "sga": 150,
        "netIncome": 120, "operatingCashFlow": 120, "totalLiabilities": 1000, "equity": 1000,
    })


def test_returns_none_without_prior():
    assert compute_beneish(_clean_year(), None) is None


def test_identical_clean_years_known_score():
    # All indices 1, TATA 0  ->  M = -4.84 + (0.92+0.528+0.404+0.892+0.115-0.172-0.327) = -2.48
    res = compute_beneish(_clean_year(), _clean_year())
    assert res is not None
    assert round(res.m_score, 2) == -2.48
    assert res.is_manipulator is False
    assert 0.0 <= res.probability <= 5.0
    assert set(res.components) == {"DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "TATA", "LVGI"}
    assert res.components["TATA"] == 0.0


def test_sample_latest_year_is_elevated():
    s = get_sample_statements()
    res = compute_beneish(s[-1], s[-2])
    assert res is not None
    # The crafted 2023 year (accruals, receivables spike, leverage) should breach -1.78.
    assert res.m_score > res.threshold
    assert res.is_manipulator is True

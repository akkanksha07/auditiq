"""Typed data models shared across the platform.

Field names use snake_case in Python but accept the camelCase aliases emitted by
the Claude extraction prompt (and used by the original prototype), so extracted
JSON validates directly via ``FinancialStatement.model_validate(...)``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high"]
Flag = Literal["ok", "medium", "high"]


# ─── Extraction target ────────────────────────────────────────────────────────
class FinancialStatement(BaseModel):
    """One year of extracted financials. All monetary values in millions."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    company_name: Optional[str] = Field(None, alias="companyName")
    year: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None

    # Income statement
    revenue: Optional[float] = None
    cogs: Optional[float] = None
    gross_profit: Optional[float] = Field(None, alias="grossProfit")
    ebit: Optional[float] = None
    net_income: Optional[float] = Field(None, alias="netIncome")
    sga: Optional[float] = None
    depreciation: Optional[float] = None
    interest_expense: Optional[float] = Field(None, alias="interestExpense")

    # Cash flow
    operating_cash_flow: Optional[float] = Field(None, alias="operatingCashFlow")

    # Balance sheet
    total_assets: Optional[float] = Field(None, alias="totalAssets")
    current_assets: Optional[float] = Field(None, alias="currentAssets")
    ppe: Optional[float] = None
    receivables: Optional[float] = None
    inventory: Optional[float] = None
    cash: Optional[float] = None
    current_liabilities: Optional[float] = Field(None, alias="currentLiabilities")
    total_liabilities: Optional[float] = Field(None, alias="totalLiabilities")
    total_debt: Optional[float] = Field(None, alias="totalDebt")
    equity: Optional[float] = None
    retained_earnings: Optional[float] = Field(None, alias="retainedEarnings")
    market_value_equity: Optional[float] = Field(None, alias="marketValueEquity")

    # Qualitative
    red_flags: list[str] = Field(default_factory=list, alias="redFlags")
    notes: Optional[str] = None

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def working_capital(self) -> Optional[float]:
        if self.current_assets is not None and self.current_liabilities is not None:
            return self.current_assets - self.current_liabilities
        return None

    @property
    def resolved_total_liabilities(self) -> Optional[float]:
        if self.total_liabilities is not None:
            return self.total_liabilities
        if self.total_assets is not None and self.equity is not None:
            return self.total_assets - self.equity
        return self.total_debt

    @property
    def resolved_gross_profit(self) -> Optional[float]:
        if self.gross_profit is not None:
            return self.gross_profit
        if self.revenue is not None and self.cogs is not None:
            return self.revenue - self.cogs
        return None


# ─── Analysis results ─────────────────────────────────────────────────────────
class BeneishResult(BaseModel):
    m_score: float
    probability: float                # probit-implied probability of manipulation (%)
    is_manipulator: bool
    threshold: float
    components: dict[str, float]       # DSRI, GMI, AQI, SGI, DEPI, SGAI, TATA, LVGI


class BenfordDigit(BaseModel):
    digit: int
    observed_count: int
    observed_pct: float
    expected_pct: float
    deviation: float                  # observed_pct - expected_pct


class BenfordResult(BaseModel):
    n: int
    digits: list[BenfordDigit]
    chi_square: float
    p_value: float
    mad: float                        # mean absolute deviation
    conformity: str                   # close | acceptable | marginal | nonconformity
    suspicious: bool
    note: Optional[str] = None        # e.g. "sample too small"


class AltmanResult(BaseModel):
    model_used: str                   # original | private | emerging
    z_score: float
    zone: RiskLevel                   # low(=safe) | medium(=grey) | high(=distress)
    zone_label: str                   # "Safe" | "Grey" | "Distress"
    components: dict[str, float]      # X1..X5


class RatioSet(BaseModel):
    receivables_days: Optional[float] = None
    inventory_days: Optional[float] = None
    gross_margin: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    asset_turnover: Optional[float] = None
    revenue_growth: Optional[float] = None


class BenchmarkRow(BaseModel):
    label: str
    company: Optional[float]
    industry: float
    unit: str
    higher_is_bad: bool
    flag: Flag


class Finding(BaseModel):
    level: RiskLevel
    category: str                     # beneish | altman | benford | benchmark | textual | clear
    title: str
    body: str
    icon: str = "•"


class NewsArticle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = "Untitled"
    source: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    sentiment: Optional[str] = None   # positive | neutral | negative


class NewsSentiment(BaseModel):
    score: float                      # -1.0 (very negative) .. +1.0 (very positive)
    label: str                        # Positive | Neutral | Negative
    summary: str
    articles: list[NewsArticle] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)  # governance/fraud signals from news
    as_of: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


# ─── Bundled per-year + full report ───────────────────────────────────────────
class YearAnalysis(BaseModel):
    year: str
    financials: FinancialStatement
    ratios: RatioSet
    benchmarks: list[BenchmarkRow] = Field(default_factory=list)
    beneish: Optional[BeneishResult] = None
    altman: Optional[AltmanResult] = None
    benford: Optional[BenfordResult] = None
    findings: list[Finding] = Field(default_factory=list)


class TrendPoint(BaseModel):
    year: str
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    m_score: Optional[float] = None
    z_score: Optional[float] = None
    gross_margin: Optional[float] = None


class Comparison(BaseModel):
    points: list[TrendPoint] = Field(default_factory=list)
    direction: str = ""               # improving | stable | worsening
    notes: list[str] = Field(default_factory=list)


class AuditReport(BaseModel):
    company_name: str
    industry: str
    years: list[YearAnalysis] = Field(default_factory=list)
    comparison: Optional[Comparison] = None
    news: Optional[NewsSentiment] = None
    summary: str = ""                 # AI narrative audit summary
    overall_risk: RiskLevel = "low"
    generated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

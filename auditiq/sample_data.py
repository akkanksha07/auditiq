"""Offline sample data (a stylised mid-size retailer) for demo mode and tests.

Numbers are crafted to surface a realistic mix of signals: accelerating
receivables, margin compression, high accruals and rising leverage in the latest
year — i.e. an elevated Beneish M-Score with mixed benchmark flags.
"""
from __future__ import annotations

from .models import DisclosureFlag, FinancialStatement, ForensicReview

SAMPLE_INDUSTRY = "retail"

_RAW = [
    {
        "companyName": "Northgate Retail Group", "year": "2021", "industry": "retail", "currency": "GBP",
        "revenue": 40000, "cogs": 27200, "grossProfit": 12800, "ebit": 3000, "netIncome": 1600,
        "sga": 9000, "depreciation": 1200, "interestExpense": 700, "operatingCashFlow": 2600,
        "totalAssets": 45000, "currentAssets": 9000, "ppe": 22000, "receivables": 1800,
        "inventory": 3500, "cash": 2000, "currentLiabilities": 9500, "totalLiabilities": 30000,
        "totalDebt": 12000, "equity": 15000, "retainedEarnings": 8000, "marketValueEquity": None,
        "redFlags": [], "notes": "Baseline year; metrics broadly in line with sector.",
    },
    {
        "companyName": "Northgate Retail Group", "year": "2022", "industry": "retail", "currency": "GBP",
        "revenue": 46000, "cogs": 32200, "grossProfit": 13800, "ebit": 3100, "netIncome": 1500,
        "sga": 10200, "depreciation": 1250, "interestExpense": 800, "operatingCashFlow": 2200,
        "totalAssets": 49000, "currentAssets": 9500, "ppe": 23000, "receivables": 2600,
        "inventory": 4200, "cash": 1600, "currentLiabilities": 10500, "totalLiabilities": 33000,
        "totalDebt": 14000, "equity": 16000, "retainedEarnings": 8800, "marketValueEquity": None,
        "redFlags": ["Receivables grew faster than revenue."],
        "notes": "Receivables and inventory building; cash conversion softening.",
    },
    {
        "companyName": "Northgate Retail Group", "year": "2023", "industry": "retail", "currency": "GBP",
        "revenue": 56000, "cogs": 41000, "grossProfit": 15000, "ebit": 2600, "netIncome": 1300,
        "sga": 11800, "depreciation": 1300, "interestExpense": 1000, "operatingCashFlow": 600,
        "totalAssets": 54000, "currentAssets": 10000, "ppe": 24000, "receivables": 5000,
        "inventory": 5200, "cash": 1200, "currentLiabilities": 12500, "totalLiabilities": 38000,
        "totalDebt": 17000, "equity": 16000, "retainedEarnings": 9000, "marketValueEquity": None,
        "redFlags": [
            "Net income materially exceeds operating cash flow (high accruals).",
            "Revenue grew 22% while operating cash flow fell — possible aggressive revenue recognition.",
            "Days sales in receivables increased sharply year on year.",
        ],
        "notes": "Change in revenue-recognition policy disclosed in notes; current ratio below 1.0.",
    },
]


def get_sample_statements() -> list[FinancialStatement]:
    return [FinancialStatement.model_validate(r) for r in _RAW]


def get_sample_benford_numbers() -> list[float]:
    """A deterministic, Benford-conforming population to demo the Benford tab.

    10**((k+0.5)/N) has a log-uniform mantissa, so first digits follow Benford by
    construction; the magnitude term just makes the values look like money.
    """
    return [round(10 ** ((k + 0.5) / 400) * (10 ** (k % 6)), 2) for k in range(400)]


def get_sample_forensic() -> ForensicReview:
    """An illustrative disclosure review for demo mode (crafted, not model output)."""
    return ForensicReview(
        summary=("Illustrative sample. The notes disclose a change in revenue-recognition "
                 "policy and growing related-party balances, and management leans on adjusted "
                 "profit measures. No going-concern language or control weaknesses are noted."),
        sections_reviewed=["Independent auditor's report", "Key audit matters",
                           "Revenue recognition", "Related parties",
                           "Alternative performance measures"],
        flags=[
            DisclosureFlag(
                category="revenue_recognition", severity="high",
                title="Revenue-recognition policy changed in the flagged year",
                detail=("The notes disclose that revenue on wholesale arrangements is now "
                        "recognised on dispatch rather than delivery, pulling roughly two "
                        "weeks of sales into the reporting period."),
                evidence=("Following a review of wholesale arrangements, revenue is now "
                          "recognised on dispatch rather than on delivery."),
                location="Note 2 — Accounting policies",
                why=("Policy changes that accelerate revenue are the most common mechanism in "
                     "earnings manipulation — and this one coincides with the receivables "
                     "spike the quantitative screens flagged."),
                innocent=["Adoption of, or alignment with, a new accounting standard.",
                          "A genuine change in shipping terms and transfer of risk."],
            ),
            DisclosureFlag(
                category="related_party", severity="medium",
                title="Growing balances with a director-linked supplier",
                detail=("Purchases from a distribution company controlled by a non-executive "
                        "director doubled year-on-year, with a quarter of the balance unpaid "
                        "at year end."),
                evidence=("Purchases from Fenwick Logistics Ltd, a company controlled by a "
                          "director, totalled £412m (2022: £198m)."),
                location="Note 28 — Related-party transactions",
                why=("Related-party channels can be used to book sales or park costs; rapid "
                     "growth in these balances warrants substantive testing."),
                innocent=["A long-standing commercial relationship, properly disclosed.",
                          "Group restructuring moving volume between entities."],
            ),
            DisclosureFlag(
                category="non_gaap", severity="medium",
                title="Heavy emphasis on 'adjusted' profit measures",
                detail=("Management commentary leads with adjusted EBITDA, excluding "
                        "restructuring, impairments and 'transformation' costs for the third "
                        "consecutive year."),
                evidence=("Adjusted EBITDA, which excludes exceptional and transformation "
                          "costs, increased 18% to £4.1bn."),
                location="Financial review",
                why=("Persistent 'exceptional' exclusions can normalise recurring costs and "
                     "widen the gap between headline and statutory profit."),
                innocent=["Genuine one-off programmes such as a disposal or restructuring.",
                          "Sector-standard APMs presented alongside statutory figures."],
            ),
        ],
    )

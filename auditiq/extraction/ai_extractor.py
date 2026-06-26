"""Claude-powered extraction of structured financials from report text."""
from __future__ import annotations

from typing import Optional

from ..config import settings
from ..intelligence.llm import complete, extract_json
from ..models import FinancialStatement

_INDUSTRIES = "retail|technology|manufacturing|financial|healthcare|energy"


def _prompt(text: str, year_label: str) -> str:
    return f"""You are an expert forensic financial analyst. Extract key figures from this annual report text.

Return ONLY valid JSON — no markdown, no backticks, no commentary. Use null for any value you cannot find. All monetary values in millions, in the report's reporting currency. Use negative numbers for losses / outflows.

JSON schema:
{{
  "companyName": string,
  "year": "{year_label}",
  "industry": "{_INDUSTRIES}",
  "currency": "GBP|USD|EUR|...",
  "revenue": number, "cogs": number, "grossProfit": number, "ebit": number,
  "netIncome": number, "sga": number, "depreciation": number, "interestExpense": number,
  "operatingCashFlow": number,
  "totalAssets": number, "currentAssets": number, "ppe": number,
  "receivables": number, "inventory": number, "cash": number,
  "currentLiabilities": number, "totalLiabilities": number, "totalDebt": number,
  "equity": number, "retainedEarnings": number, "marketValueEquity": number,
  "redFlags": [string, ...],
  "notes": string
}}

Guidance:
- "ebit" = operating profit, before interest and tax.
- "totalDebt" = interest-bearing borrowings (short + long term); "totalLiabilities" = all liabilities.
- "marketValueEquity" only if a market capitalisation is stated, else null.
- "redFlags": concrete textual warning signs — going-concern doubt, restatements, auditor
  qualifications, related-party transactions, accounting-policy changes, large one-off items.
- "notes": brief commentary on anything unusual in accounting policies or the notes.

Annual report text (truncated):
{text[:15000]}"""


def extract_financials(
    text: str, year_label: str, model: Optional[str] = None
) -> FinancialStatement:
    raw = complete(_prompt(text, year_label), model=model or settings.extraction_model, max_tokens=1500)
    data = extract_json(raw)
    if not isinstance(data, dict):
        raise ValueError("Extraction did not return a JSON object.")
    data.setdefault("year", year_label)
    return FinancialStatement.model_validate(data)

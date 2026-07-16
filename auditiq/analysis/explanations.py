"""Plain-English explanations for every screening flag.

AuditIQ's quantitative checks are *screening heuristics*, not verdicts. For each
flag type this module supplies a pair ``(why, innocent)``: what specifically
tripped the screen, and the common benign explanations a forensic accountant
would rule out before reading anything sinister into it.
"""
from __future__ import annotations

from ..models import BenchmarkRow

# What each elevated Beneish index actually means, in plain English.
_DRIVER_MEANING = {
    "DSRI": "receivables grew faster than revenue",
    "GMI": "gross margin deteriorated year-on-year",
    "AQI": "'soft' assets (intangibles, deferred costs) grew as a share of total assets",
    "SGI": "sales grew unusually fast",
    "DEPI": "the depreciation rate slowed",
    "SGAI": "overheads outpaced sales",
    "TATA": "reported profit is not backed by operating cash flow",
    "LVGI": "leverage increased",
}

_BENEISH_INNOCENT = [
    "Rapid but legitimate growth inflates receivables and accruals in exactly the same way.",
    "An acquisition or disposal changes the year-on-year balance-sheet mix.",
    "A new revenue standard (e.g. IFRS 15) shifts the timing of revenue and receivables.",
    "The model was calibrated on 1980s–90s US manufacturers; it over-flags modern, "
    "high-growth, or asset-light businesses.",
]

_ALTMAN_INNOCENT = [
    "Heavy but planned capital investment or leverage (infrastructure, LBOs, growth capex).",
    "Early-stage, cyclical, or deliberate turnaround situations score poorly without being distressed.",
    "Asset-light or structurally thin-margin sectors sit low on the scale by design.",
    "The selected Z-Score variant may simply be a poor fit for this company's sector.",
]

_BENFORD_INNOCENT = [
    "Published statements are rounded and aggregated, which distorts Benford's curve "
    "regardless of any manipulation.",
    "Fixed price points and pricing psychology (e.g. products priced at 9.99) skew leading "
    "digits — this is why a Benford test 'flags' companies like Apple that are manipulating nothing.",
    "The numeric sample from one report is small; Benford is only truly diagnostic on large, "
    "transaction-level datasets such as journal entries or invoices.",
    "Currency translation and unit choices (thousands vs millions) shift digit patterns.",
]

_BENCHMARK_INNOCENT = [
    "A deliberate strategy — premium vs discount positioning, or a different business model.",
    "Different but perfectly legitimate accounting policies compared with peers.",
    "Scale, geography, or product-mix differences within the same broad sector.",
    "The benchmark is a broad sector average, not a matched comparable set.",
]

_TEXTUAL_INNOCENT = [
    "May be routine, standards-required boilerplate — read the surrounding context.",
    "Transparent disclosure of a known issue is often a sign of good governance, not bad.",
]


def beneish_explanation(drivers: list[str]) -> tuple[str, list[str]]:
    meanings = [f"{d} ({_DRIVER_MEANING[d]})" for d in drivers if d in _DRIVER_MEANING]
    lead = "; ".join(meanings) if meanings else "several indices moved together"
    why = ("The M-Score combines eight year-on-year indices. The screen tripped mainly because "
           f"{lead}. Each movement can be normal on its own — it is the combination that "
           "matches the statistical pattern of past manipulators.")
    return why, list(_BENEISH_INNOCENT)


def altman_explanation(zone: str, model_used: str) -> tuple[str, list[str]]:
    band = "distress" if zone == "high" else "grey"
    why = (f"The Z-Score blends working capital, retained earnings, EBIT, leverage and asset "
           f"turnover into one solvency screen; this company's mix lands in the {band} band of "
           f"the {model_used} variant.")
    return why, list(_ALTMAN_INNOCENT)


def benford_explanation(mad: float, n: int) -> tuple[str, list[str]]:
    why = (f"Across {n} numbers, leading digits deviate from Benford's expected curve "
           f"(1 should lead ~30% of the time, 9 under 5%; deviation MAD {mad}). On published, "
           "aggregated accounts this is a weak signal — treat it as a prompt to look at the "
           "underlying numeric population, never as evidence by itself.")
    return why, list(_BENFORD_INNOCENT)


def benchmark_explanation(row: BenchmarkRow) -> tuple[str, list[str]]:
    if row.company is None:
        direction = "unavailable for comparison against"
    else:
        direction = "above" if row.company > row.industry else "below"
    why = (f"{row.label} is {direction} the sector average by enough to breach the screening "
           f"band. Sustained, unexplained deviations from peers are where forensic reviews start.")
    return why, list(_BENCHMARK_INNOCENT)


def textual_explanation() -> tuple[str, list[str]]:
    why = ("Flagged from the report's own wording during extraction — language of the kind "
           "that often accompanies accounting risk.")
    return why, list(_TEXTUAL_INNOCENT)

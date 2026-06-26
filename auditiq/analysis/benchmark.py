"""Benchmark a company's ratios against industry averages."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from ..config import BENCHMARKS_PATH
from ..models import BenchmarkRow, Flag, RatioSet


@lru_cache(maxsize=1)
def load_benchmarks() -> dict:
    with open(BENCHMARKS_PATH, encoding="utf-8") as f:
        return json.load(f)


def industries() -> list[tuple[str, str]]:
    """[(key, label), …] for populating selectors."""
    return [(k, v["label"]) for k, v in load_benchmarks().items()]


def _flag_high(value: Optional[float], bench: float, high: float, med: float) -> Flag:
    """Higher-is-worse metric: flag when value exceeds multiples of the benchmark."""
    if value is None:
        return "ok"
    if value > bench * high:
        return "high"
    if value > bench * med:
        return "medium"
    return "ok"


def benchmark_ratios(ratios: RatioSet, industry: str) -> list[BenchmarkRow]:
    bench = load_benchmarks().get(industry)
    if not bench:
        return []

    rows: list[BenchmarkRow] = []

    # Receivables days — higher is worse
    rows.append(BenchmarkRow(
        label="Receivables Days", company=ratios.receivables_days,
        industry=bench["receivablesDays"], unit="d", higher_is_bad=True,
        flag=_flag_high(ratios.receivables_days, bench["receivablesDays"], 1.3, 1.1),
    ))

    # Gross margin (%) — lower is worse
    gm = ratios.gross_margin
    gm_flag: Flag = "ok"
    if gm is not None:
        if gm < bench["grossMargin"] * 0.8:
            gm_flag = "high"
        elif gm < bench["grossMargin"] * 0.9:
            gm_flag = "medium"
    rows.append(BenchmarkRow(
        label="Gross Margin", company=round(gm * 100, 1) if gm is not None else None,
        industry=round(bench["grossMargin"] * 100, 1), unit="%", higher_is_bad=False, flag=gm_flag,
    ))

    # Current ratio — lower is worse (and < 1.0 is a hard flag)
    cr = ratios.current_ratio
    cr_flag: Flag = "ok"
    if cr is not None:
        if cr < 1.0:
            cr_flag = "high"
        elif cr < bench["currentRatio"] * 0.85:
            cr_flag = "medium"
    rows.append(BenchmarkRow(
        label="Current Ratio", company=cr, industry=bench["currentRatio"],
        unit="x", higher_is_bad=False, flag=cr_flag,
    ))

    # Debt / equity — higher is worse
    rows.append(BenchmarkRow(
        label="Debt / Equity", company=ratios.debt_to_equity,
        industry=bench["debtToEquity"], unit="x", higher_is_bad=True,
        flag=_flag_high(ratios.debt_to_equity, bench["debtToEquity"], 1.5, 1.2),
    ))

    # Interest coverage — lower is worse (< 2.0 is a hard flag)
    ic = ratios.interest_coverage
    ic_flag: Flag = "ok"
    if ic is not None:
        if ic < 2.0:
            ic_flag = "high"
        elif ic < bench["interestCoverage"] * 0.7:
            ic_flag = "medium"
    rows.append(BenchmarkRow(
        label="Interest Coverage", company=ic, industry=bench["interestCoverage"],
        unit="x", higher_is_bad=False, flag=ic_flag,
    ))

    # Asset turnover — lower is mildly concerning
    at = ratios.asset_turnover
    at_flag: Flag = "medium" if (at is not None and at < bench["assetTurnover"] * 0.6) else "ok"
    rows.append(BenchmarkRow(
        label="Asset Turnover", company=at, industry=bench["assetTurnover"],
        unit="x", higher_is_bad=False, flag=at_flag,
    ))

    return rows

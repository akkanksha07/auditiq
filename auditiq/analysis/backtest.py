"""Back-testing / validation harness.

Runs the *existing* screens over a labelled set of well-known manipulators and
matched clean peers, and reports a confusion matrix, sensitivity (hit-rate) and
false-positive rate per screen. It adds no new calculation — it exercises the
same engines the app uses. The point is honesty: it measures where the screens
work, where they miss (e.g. fabricated-cash frauds that never distort the
ratios), and how often they flag a perfectly healthy company.

CLI:  python -m auditiq.analysis.backtest
"""
from __future__ import annotations

import json
from typing import Callable

from ..config import PKG_DIR
from ..models import (
    BacktestResult, BacktestRow, BacktestScreen, ConfusionMatrix, FinancialStatement,
)
from .altman import compute_altman
from .benchmark import benchmark_ratios
from .beneish import compute_beneish
from .findings import build_findings
from .ratios import compute_ratios
from .scoring import assess_tiers

CASES_PATH = PKG_DIR / "data" / "backtest_cases.json"


def load_cases() -> dict:
    with open(CASES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _row(case: dict) -> BacktestRow:
    sector = case["sector"]
    cur = FinancialStatement.model_validate(
        {**case["current"], "industry": sector, "companyName": case["company"],
         "year": case.get("year", "")})
    prior = FinancialStatement.model_validate({**case["prior"], "industry": sector})

    ratios = compute_ratios(cur, prior)
    beneish = compute_beneish(cur, prior)
    altman = compute_altman(cur, industry=sector)
    findings = build_findings(cur, beneish, altman, None, benchmark_ratios(ratios, sector))
    tiered = assess_tiers(findings, None)

    return BacktestRow(
        company=case["company"], sector=sector, year=case.get("year", ""),
        is_manipulator=(case["label"] == "manipulator"),
        m_score=beneish.m_score if beneish else None,
        beneish_flag=bool(beneish and beneish.is_manipulator),
        z_score=altman.z_score if altman else None,
        altman_zone=altman.zone_label if altman else None,
        altman_flag=bool(altman and altman.zone == "high"),
        tiered_flag=(tiered.level in ("high", "medium") and tiered.substantive > 0),
    )


def _matrix(rows: list[BacktestRow], predict: Callable[[BacktestRow], bool]) -> ConfusionMatrix:
    m = ConfusionMatrix()
    for r in rows:
        pred, pos = predict(r), r.is_manipulator
        if pos and pred:
            m.tp += 1
        elif not pos and pred:
            m.fp += 1
        elif not pos and not pred:
            m.tn += 1
        else:
            m.fn += 1
    return m


def run_backtest() -> BacktestResult:
    data = load_cases()
    rows = [_row(c) for c in data["cases"]]
    screens = [
        BacktestScreen(name="Beneish M-Score", matrix=_matrix(rows, lambda r: r.beneish_flag)),
        BacktestScreen(name="Altman Z-Score (distress)", matrix=_matrix(rows, lambda r: r.altman_flag)),
        BacktestScreen(name="Tiered screen (Tier 1+2)", matrix=_matrix(rows, lambda r: r.tiered_flag)),
        BacktestScreen(name="Any quantitative screen",
                       matrix=_matrix(rows, lambda r: r.beneish_flag or r.altman_flag)),
    ]
    return BacktestResult(
        rows=rows, screens=screens,
        n_manipulators=sum(r.is_manipulator for r in rows),
        n_clean=sum(not r.is_manipulator for r in rows),
        caveats=data.get("caveats", []),
    )


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def main() -> None:
    res = run_backtest()
    print(f"\nAuditIQ back-test — {res.n_manipulators} known manipulators "
          f"vs {res.n_clean} matched clean peers\n")
    hdr = f"{'Company':20}{'Label':8}{'M-Score':>9}{'Z-Score':>9}{'Altman':>10}{'Flagged':>9}"
    print(hdr)
    print("-" * len(hdr))
    for r in res.rows:
        ms = f"{r.m_score:.2f}" if r.m_score is not None else "-"
        zs = f"{r.z_score:.2f}" if r.z_score is not None else "-"
        print(f"{r.company:20}{'MANIP' if r.is_manipulator else 'clean':8}"
              f"{ms:>9}{zs:>9}{(r.altman_zone or '-'):>10}"
              f"{'YES' if r.tiered_flag else 'no':>9}")
    print()
    for s in res.screens:
        m = s.matrix
        print(f"{s.name:28} TP {m.tp}  FP {m.fp}  TN {m.tn}  FN {m.fn}   "
              f"sensitivity {_pct(m.sensitivity):>4} · FPR {_pct(m.false_positive_rate):>4} · "
              f"accuracy {_pct(m.accuracy):>4}")
    print()
    for c in res.caveats:
        print("  -", c)
    print()


if __name__ == "__main__":
    main()

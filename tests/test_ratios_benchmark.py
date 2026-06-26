"""Tests for ratio computation and industry benchmarking."""
import math

from auditiq.analysis.benchmark import benchmark_ratios, industries, load_benchmarks
from auditiq.analysis.ratios import compute_ratios
from auditiq.sample_data import get_sample_statements


def test_ratios_on_sample():
    latest = get_sample_statements()[-1]  # 2023
    r = compute_ratios(latest)
    assert math.isclose(r.receivables_days, 5000 * 365 / 56000, rel_tol=1e-3)
    assert math.isclose(r.gross_margin, 15000 / 56000, rel_tol=1e-3)
    assert r.current_ratio == 0.8


def test_benchmark_flags():
    latest = get_sample_statements()[-1]
    rows = {b.label: b for b in benchmark_ratios(compute_ratios(latest), "retail")}
    # Current ratio below 1.0 is a hard high flag.
    assert rows["Current Ratio"].flag == "high"
    # Receivables days 27.4 vs benchmark 18 (> 1.3x) -> high.
    assert rows["Receivables Days"].flag == "high"


def test_benchmarks_data_integrity():
    data = load_benchmarks()
    assert set(k for k, _ in industries()) == set(data)
    for sector in data.values():
        for key in ("receivablesDays", "grossMargin", "currentRatio", "debtToEquity"):
            assert key in sector

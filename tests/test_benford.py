"""Tests for the Benford's Law engine."""
import math

from auditiq.analysis.benford import EXPECTED, analyze, extract_numbers, first_digit


def test_expected_distribution_sums_to_one():
    assert math.isclose(sum(EXPECTED.values()), 1.0, abs_tol=1e-9)
    assert round(EXPECTED[1] * 100, 1) == 30.1  # canonical Benford value


def test_first_digit():
    assert first_digit(0.0123) == 1
    assert first_digit(-540) == 5
    assert first_digit(98765) == 9
    assert first_digit(0) is None


def test_extract_numbers_handles_formats():
    nums = extract_numbers("Revenue 1,234.5; provision (567); cash £89; note 4")
    assert 1234.5 in nums
    assert -567 in nums
    assert 89 in nums


def test_conforming_vs_nonconforming():
    # Strongly non-Benford: 60 values all starting with 9.
    bad = analyze([9 * 10 ** (i % 3) for i in range(60)])
    assert bad.n == 60
    assert bad.conformity == "nonconformity"
    assert bad.suspicious is True
    assert 0.0 <= bad.p_value <= 1.0

    # Small sample -> flagged as not meaningful, never "suspicious".
    small = analyze([1, 2, 3, 4, 5])
    assert small.suspicious is False
    assert small.note is not None

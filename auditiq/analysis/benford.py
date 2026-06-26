"""Benford's Law — first-digit distribution analysis for manipulation detection.

Genuine accounting populations follow Benford's Law: P(first digit = d) =
log10(1 + 1/d). Large deviations (high MAD / significant chi-square) can indicate
fabricated or rounded figures. Reliable only on reasonably large samples.
"""
from __future__ import annotations

import math
import re
from typing import Iterable, Optional

from scipy.stats import chisquare

from ..config import BENFORD_MAD_THRESHOLDS, BENFORD_MIN_SAMPLE
from ..models import BenfordDigit, BenfordResult

EXPECTED: dict[int, float] = {d: math.log10(1 + 1 / d) for d in range(1, 10)}

# Number-like tokens: optional currency/sign, thousands separators, decimals,
# and accounting-style parentheses for negatives.
_NUM_RE = re.compile(r"\(?[-+]?[$£€]?\s?\d[\d,]*(?:\.\d+)?\)?")


def first_digit(value: float) -> Optional[int]:
    v = abs(value)
    if v == 0:
        return None
    while v < 1:
        v *= 10
    while v >= 10:
        v /= 10
    return int(v)


def extract_numbers(text: str) -> list[float]:
    """Pull plausible financial numbers (|x| >= 1) from raw report text."""
    out: list[float] = []
    for tok in _NUM_RE.findall(text):
        neg = tok.strip().startswith("(") and tok.strip().endswith(")")
        cleaned = re.sub(r"[(),$£€+\s]", "", tok).lstrip("-")
        if not cleaned or cleaned == ".":
            continue
        try:
            val = float(cleaned)
        except ValueError:
            continue
        if neg:
            val = -val
        if abs(val) >= 1:
            out.append(val)
    return out


def _conformity(mad: float) -> str:
    t = BENFORD_MAD_THRESHOLDS
    if mad < t["close"]:
        return "close"
    if mad < t["acceptable"]:
        return "acceptable"
    if mad < t["marginal"]:
        return "marginal"
    return "nonconformity"


def analyze(numbers: Iterable[float]) -> BenfordResult:
    digits = [d for d in (first_digit(n) for n in numbers) if d is not None]
    n = len(digits)

    counts = {d: 0 for d in range(1, 10)}
    for d in digits:
        counts[d] += 1

    rows: list[BenfordDigit] = []
    obs_freq: list[float] = []
    exp_freq: list[float] = []
    for d in range(1, 10):
        obs_pct = counts[d] / n if n else 0.0
        exp_pct = EXPECTED[d]
        rows.append(BenfordDigit(
            digit=d, observed_count=counts[d],
            observed_pct=round(obs_pct * 100, 2),
            expected_pct=round(exp_pct * 100, 2),
            deviation=round((obs_pct - exp_pct) * 100, 2),
        ))
        obs_freq.append(counts[d])
        exp_freq.append(exp_pct * n)

    mad = sum(abs(r.observed_pct - r.expected_pct) / 100 for r in rows) / 9

    if n > 0 and all(e > 0 for e in exp_freq):
        chi, p = chisquare(f_obs=obs_freq, f_exp=exp_freq)
        chi, p = float(chi), float(p)
    else:
        chi, p = 0.0, 1.0

    conformity = _conformity(mad)
    suspicious = conformity in ("marginal", "nonconformity") or p < 0.05
    note: Optional[str] = None
    if n < BENFORD_MIN_SAMPLE:
        note = (f"Only {n} numbers sampled; Benford analysis needs "
                f">= {BENFORD_MIN_SAMPLE} values to be reliable.")
        suspicious = False

    return BenfordResult(
        n=n, digits=rows, chi_square=round(chi, 2), p_value=round(p, 4),
        mad=round(mad, 5), conformity=conformity, suspicious=suspicious, note=note,
    )


def analyze_text(text: str) -> BenfordResult:
    return analyze(extract_numbers(text))

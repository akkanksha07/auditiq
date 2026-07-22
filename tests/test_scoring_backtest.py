"""Tests for tier-weighted scoring and the back-testing harness."""
from auditiq.analysis.backtest import run_backtest
from auditiq.analysis.scoring import assess_tiers, finding_tier
from auditiq.models import ConfusionMatrix, DisclosureFlag, Finding


def test_finding_tier_map():
    assert finding_tier("beneish") == 1
    assert finding_tier("altman") == 1
    assert finding_tier("textual") == 2
    assert finding_tier("benchmark") == 3
    assert finding_tier("benford") == 3
    assert finding_tier("clear") == 0


def test_tier3_is_context_not_headline():
    # "Apple-like": only peer-outlier (Tier 3) flags -> no substantive flags, headline stays low.
    f = [Finding(level="high", category="benchmark", title="Margin off sector", body="", tier=3),
         Finding(level="medium", category="benford", title="Benford deviation", body="", tier=3)]
    ta = assess_tiers(f, [])
    assert ta.substantive == 0
    assert ta.level == "low"
    assert ta.context == 2


def test_substantive_flags_drive_headline():
    f = [Finding(level="high", category="beneish", title="Beneish", body="", tier=1),
         Finding(level="high", category="benchmark", title="bmark", body="", tier=3)]
    disc = [DisclosureFlag(category="going_concern", severity="high", title="Going concern")]
    ta = assess_tiers(f, disc)
    assert ta.level == "high"
    assert ta.t1 == 1 and ta.t2 == 1          # one Tier-1 finding + one disclosure flag
    assert ta.substantive == 2
    assert ta.context == 1


def test_confusion_matrix_math():
    m = ConfusionMatrix(tp=3, fp=1, tn=6, fn=4)
    assert m.n == 14
    assert abs(m.sensitivity - 3 / 7) < 1e-9
    assert abs(m.false_positive_rate - 1 / 7) < 1e-9
    assert abs(m.accuracy - 9 / 14) < 1e-9
    assert ConfusionMatrix().sensitivity == 0.0   # no divide-by-zero on an empty matrix


def test_backtest_runs_and_outlier_not_flagged():
    res = run_backtest()
    assert res.n_manipulators == 7 and res.n_clean == 7
    for s in res.screens:
        assert s.matrix.n == 14
        assert 0.0 <= s.matrix.sensitivity <= 1.0
        assert 0.0 <= s.matrix.false_positive_rate <= 1.0
    by = {r.company: r for r in res.rows}
    assert by["Apple"].is_manipulator is False
    assert by["Apple"].tiered_flag is False       # the healthy outlier is NOT flagged
    assert by["Enron"].tiered_flag is True         # a real fraud IS flagged
    assert any(r.is_manipulator and r.tiered_flag for r in res.rows)

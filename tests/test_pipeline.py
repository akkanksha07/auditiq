"""End-to-end (offline) test of the analysis pipeline."""
from auditiq.pipeline import build_report
from auditiq.sample_data import SAMPLE_INDUSTRY, get_sample_statements


def test_build_report_offline():
    report = build_report(get_sample_statements(), industry=SAMPLE_INDUSTRY)

    assert report.company_name == "Northgate Retail Group"
    assert len(report.years) == 3

    # First year has no prior -> no Beneish; later years do.
    assert report.years[0].beneish is None
    assert report.years[-1].beneish is not None
    assert report.years[-1].altman is not None

    # Multi-year comparison is built and trends are captured.
    assert report.comparison is not None
    assert len(report.comparison.points) == 3
    assert report.comparison.direction in {"improving", "stable", "worsening"}

    # Crafted sample should surface real findings (not the "all clear" case).
    assert report.overall_risk in {"medium", "high"}
    assert any(f.category != "clear" for f in report.years[-1].findings)

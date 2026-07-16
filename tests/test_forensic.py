"""Tests for reframed findings (why/innocent) and the forensic disclosure layer."""
from auditiq.analysis.benchmark import benchmark_ratios
from auditiq.analysis.beneish import compute_beneish
from auditiq.analysis.findings import build_findings
from auditiq.analysis.ratios import compute_ratios
from auditiq.intelligence.forensic import _locate_sections, parse_review
from auditiq.sample_data import SAMPLE_INDUSTRY, get_sample_forensic, get_sample_statements


def test_findings_carry_why_and_innocent():
    s = get_sample_statements()
    latest, prior = s[-1], s[-2]
    ratios = compute_ratios(latest, prior)
    findings = build_findings(latest, compute_beneish(latest, prior), None, None,
                              benchmark_ratios(ratios, SAMPLE_INDUSTRY))
    beneish = next(f for f in findings if f.category == "beneish")
    assert beneish.why and "indices" in beneish.why
    assert len(beneish.innocent) >= 3
    bench = next(f for f in findings if f.category == "benchmark")
    assert bench.why and bench.innocent


def test_parse_review_normalises_model_output():
    data = {
        "summary": "ok",
        "flags": [
            {"category": "going_concern", "severity": "HIGH", "title": "t", "detail": "d",
             "evidence": "q", "why": "w", "innocent": "single string"},
            {"category": "made_up_category", "severity": "weird", "title": "t2", "detail": "d2"},
            "not a dict",
        ],
    }
    fr = parse_review(data, ["Going concern"])
    assert fr is not None and len(fr.flags) == 2
    assert fr.flags[0].severity == "high" and fr.flags[0].innocent == ["single string"]
    assert fr.flags[1].category == "other" and fr.flags[1].severity == "medium"
    assert fr.sections_reviewed == ["Going concern"]
    assert parse_review("nope") is None


def test_locate_sections_finds_headings():
    text = ("blah " * 200) + "Independent Auditor's Report to the members" + (" blah" * 200) \
           + " Key Audit Matters were as follows " + ("x " * 50) + " Related party transactions"
    bundle, found = _locate_sections(text)
    assert "Independent auditor's report" in found
    assert "Key audit matters" in found
    assert "Related parties" in found
    assert "auditor" in bundle.lower()


def test_sample_forensic_is_well_formed():
    fr = get_sample_forensic()
    assert fr.flags and all(f.evidence for f in fr.flags)
    assert all(f.why and f.innocent for f in fr.flags)
    assert fr.flags[0].severity == "high"

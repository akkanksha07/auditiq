"""Generate a professional PDF forensic audit report with reportlab."""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    HRFlowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from ..config import REPORT_DIR
from ..models import AuditReport, YearAnalysis

# ─── Brand palette ────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#0a0f1e")
ACCENT = colors.HexColor("#3b82f6")
GREEN = colors.HexColor("#10b981")
AMBER = colors.HexColor("#f59e0b")
RED = colors.HexColor("#ef4444")
GREY = colors.HexColor("#64748b")
LIGHT = colors.HexColor("#eef2f9")
WHITE = colors.white

RISK_COLOR = {"low": GREEN, "medium": AMBER, "high": RED}
RISK_LABEL = {"low": "LOW RISK", "medium": "ELEVATED RISK", "high": "HIGH RISK"}
FLAG_COLOR = {"ok": GREEN, "medium": AMBER, "high": RED}
LEVEL_COLOR = {"low": GREEN, "medium": AMBER, "high": RED}

_PAGE_W = A4[0]
_CONTENT_W = _PAGE_W - 36 * mm  # left+right margins of 18mm each


# ─── Styles ───────────────────────────────────────────────────────────────────
def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Brand", parent=ss["Title"], textColor=WHITE, fontSize=26,
                          alignment=TA_LEFT, spaceAfter=2, leading=30))
    ss.add(ParagraphStyle("CoverSub", parent=ss["Normal"], textColor=LIGHT, fontSize=11,
                          alignment=TA_LEFT))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], textColor=NAVY, fontSize=14,
                          spaceBefore=14, spaceAfter=6))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=9.5, leading=14,
                          textColor=colors.HexColor("#1f2937")))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=8, leading=11, textColor=GREY))
    ss.add(ParagraphStyle("FindTitle", parent=ss["Normal"], fontSize=10, leading=13,
                          textColor=NAVY, fontName="Helvetica-Bold"))
    return ss


def _fig_image(fig, width_mm: float) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    w, h = fig.get_size_inches()
    img = Image(buf, width=width_mm * mm, height=width_mm * mm * (h / w))
    return img


# ─── Charts ───────────────────────────────────────────────────────────────────
def _benford_fig(year: YearAnalysis):
    bf = year.benford
    digits = [d.digit for d in bf.digits]
    obs = [d.observed_pct for d in bf.digits]
    exp = [d.expected_pct for d in bf.digits]
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.bar(digits, obs, color="#3b82f6", alpha=0.85, label="Observed")
    ax.plot(digits, exp, color="#ef4444", marker="o", linewidth=1.6, label="Benford expected")
    ax.set_xlabel("Leading digit"); ax.set_ylabel("% of values")
    ax.set_xticks(digits); ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.2)
    return fig


def _trend_fig(report: AuditReport):
    pts = report.comparison.points
    years = [p.year for p in pts]
    ms = [p.m_score for p in pts]
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    if any(m is not None for m in ms):
        ax.plot(years, ms, color="#f59e0b", marker="o", linewidth=2, label="M-Score")
        ax.axhline(-1.78, color="#ef4444", linestyle="--", linewidth=1, label="Threshold -1.78")
        ax.set_ylabel("Beneish M-Score"); ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.2)
    return fig


# ─── Section builders ─────────────────────────────────────────────────────────
def _cover(report: AuditReport, ss) -> list:
    risk = report.overall_risk
    banner = Table(
        [[Paragraph("AuditIQ", ss["Brand"])],
         [Paragraph("Forensic Audit Intelligence Report", ss["CoverSub"])]],
        colWidths=[_CONTENT_W],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 16), ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (0, 0), 18), ("BOTTOMPADDING", (-1, -1), (-1, -1), 18),
    ]))

    badge = Table([[Paragraph(f"<b>{RISK_LABEL[risk]}</b>", ParagraphStyle(
        "badge", textColor=WHITE, fontSize=12, alignment=TA_CENTER))]], colWidths=[60 * mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RISK_COLOR[risk]),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    meta = [
        ["Company", report.company_name],
        ["Industry", report.industry.title()],
        ["Years analysed", ", ".join(y.year for y in report.years) or "—"],
        ["Generated", report.generated_at],
    ]
    meta_tbl = Table(meta, colWidths=[40 * mm, _CONTENT_W - 40 * mm])
    meta_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10), ("TEXTCOLOR", (0, 0), (0, -1), GREY),
        ("TEXTCOLOR", (1, 0), (1, -1), NAVY), ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LINEBELOW", (0, 0), (-1, -2), 0.4, LIGHT),
    ]))

    return [banner, Spacer(1, 14), badge, Spacer(1, 16), meta_tbl, Spacer(1, 10),
            Paragraph("Not a substitute for qualified audit advice. All scores are model "
                      "estimates for screening purposes and must be reviewed by a professional.",
                      ss["Small"])]


def _summary(report: AuditReport, ss) -> list:
    out = [Paragraph("Executive Summary", ss["H2"]),
           HRFlowable(width="100%", thickness=0.6, color=LIGHT)]
    if report.summary:
        out.append(Paragraph(report.summary, ss["Body"]))
    else:
        out.append(Paragraph("AI narrative summary not available (no API key configured). "
                             "Quantitative findings are detailed below.", ss["Body"]))
    return out


def _metrics(year: YearAnalysis, ss) -> list:
    b, a, r = year.beneish, year.altman, year.ratios
    rows = [["Metric", "Value", "Read"]]
    if b:
        rows.append(["Beneish M-Score", f"{b.m_score}",
                     "Manipulator zone" if b.is_manipulator else "Non-manipulator"])
        rows.append(["Fraud probability (probit)", f"{b.probability}%", ""])
    if a:
        rows.append(["Altman Z-Score", f"{a.z_score} ({a.model_used})", a.zone_label])
    if r.gross_margin is not None:
        rows.append(["Gross margin", f"{r.gross_margin * 100:.1f}%", ""])
    if r.current_ratio is not None:
        rows.append(["Current ratio", f"{r.current_ratio}x", ""])
    if r.receivables_days is not None:
        rows.append(["Receivables days", f"{r.receivables_days:.0f}d", ""])

    tbl = Table(rows, colWidths=[55 * mm, 45 * mm, _CONTENT_W - 100 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [Paragraph(f"Key Metrics — {year.year}", ss["H2"]), tbl]


def _findings(year: YearAnalysis, ss) -> list:
    out = [Paragraph(f"Findings — {year.year}", ss["H2"])]
    for f in year.findings:
        chip = Table([[Paragraph(f"<b>{f.level.upper()}</b>", ParagraphStyle(
            "lvl", textColor=WHITE, fontSize=7, alignment=TA_CENTER))]], colWidths=[20 * mm])
        chip.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LEVEL_COLOR[f.level]),
                                  ("TOPPADDING", (0, 0), (-1, -1), 2),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        body = [Paragraph(f.title, ss["FindTitle"]), Paragraph(f.body, ss["Body"])]
        row = Table([[chip, body]], colWidths=[24 * mm, _CONTENT_W - 24 * mm])
        row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        out.append(row)
    return out


def _beneish_table(year: YearAnalysis, ss) -> list:
    from ..analysis.beneish import COMPONENT_INFO
    b = year.beneish
    if not b:
        return []
    rows = [["Indicator", "Value", "What it measures"]]
    for k, v in b.components.items():
        name = COMPONENT_INFO.get(k, (k, "", 0))[0]
        rows.append([f"{k} — {name}", f"{v}", COMPONENT_INFO.get(k, ("", "", 0))[1]])
    tbl = Table(rows, colWidths=[55 * mm, 20 * mm, _CONTENT_W - 75 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [Paragraph("Beneish M-Score Components", ss["H2"]), tbl]


def _benchmark_table(year: YearAnalysis, ss) -> list:
    if not year.benchmarks:
        return []
    rows = [["Metric", "Company", "Industry", "Status"]]
    styles = []
    for i, b in enumerate(year.benchmarks, start=1):
        comp = "N/A" if b.company is None else f"{b.company}{b.unit}"
        rows.append([b.label, comp, f"{b.industry}{b.unit}", b.flag.upper()])
        styles.append(("TEXTCOLOR", (3, i), (3, i), FLAG_COLOR[b.flag]))
    tbl = Table(rows, colWidths=[55 * mm, 35 * mm, 35 * mm, _CONTENT_W - 125 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        *styles,
    ]))
    return [Paragraph(f"Industry Benchmarking — {year.year}", ss["H2"]), tbl]


def _news(report: AuditReport, ss) -> list:
    n = report.news
    if not n:
        return []
    out = [Paragraph("News Sentiment Cross-Reference", ss["H2"]),
           Paragraph(f"<b>Overall sentiment:</b> {n.label} ({n.score:+.2f}) — as of {n.as_of}", ss["Body"]),
           Paragraph(n.summary, ss["Body"])]
    if n.flags:
        out.append(Paragraph("<b>Signals:</b> " + "; ".join(n.flags), ss["Body"]))
    for art in n.articles[:6]:
        src = f" — {art.source}" if art.source else ""
        out.append(Paragraph(f"• {art.title}{src} ({art.date or 'n/a'})", ss["Small"]))
    return out


def _methodology(ss) -> list:
    txt = (
        "<b>Beneish M-Score</b> — eight-factor probit model of earnings manipulation; "
        "scores above -1.78 indicate likely manipulation. "
        "<b>Altman Z-Score</b> — distress model (original / private / emerging-market variants) "
        "classifying solvency into safe, grey and distress zones. "
        "<b>Benford's Law</b> — first-digit distribution test; large deviations (MAD / chi-square) "
        "can indicate fabricated or rounded figures. "
        "<b>Benchmarking</b> — ratios compared against sector averages with severity flags."
    )
    return [PageBreak(), Paragraph("Methodology", ss["H2"]),
            HRFlowable(width="100%", thickness=0.6, color=LIGHT),
            Paragraph(txt, ss["Body"]), Spacer(1, 8),
            Paragraph("Disclaimer: AuditIQ is an analytical screening tool, not an audit. "
                      "Outputs are model estimates and may reflect extraction error from the "
                      "source PDF. Decisions must rest on professional judgement.", ss["Small"])]


# ─── Public API ───────────────────────────────────────────────────────────────
def _build_story(report: AuditReport, ss) -> list:
    story = _cover(report, ss)
    story += [Spacer(1, 14)] + _summary(report, ss)

    latest = report.years[-1] if report.years else None
    if latest:
        story += [Spacer(1, 8)] + _metrics(latest, ss)
        story += [Spacer(1, 6)] + _findings(latest, ss)
        story += [PageBreak()] + _beneish_table(latest, ss)
        if latest.benford and latest.benford.n:
            story += [Spacer(1, 8), Paragraph("Benford's Law Analysis", ss["H2"]),
                      _fig_image(_benford_fig(latest), 160)]
            if latest.benford.note:
                story.append(Paragraph(latest.benford.note, ss["Small"]))
        story += [Spacer(1, 8)] + _benchmark_table(latest, ss)

    if report.comparison and len(report.comparison.points) >= 2:
        story += [Spacer(1, 10), Paragraph("Multi-Year Trend", ss["H2"]),
                  _fig_image(_trend_fig(report), 160)]
        story += [Paragraph(f"Direction of travel: <b>{report.comparison.direction}</b>.", ss["Body"])]
        for note in report.comparison.notes:
            story.append(Paragraph(f"• {note}", ss["Small"]))

    story += [Spacer(1, 8)] + _news(report, ss)
    story += _methodology(ss)
    return story


def report_bytes(report: AuditReport) -> bytes:
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title="AuditIQ Report")
    doc.build(_build_story(report, ss))
    buf.seek(0)
    return buf.getvalue()


def generate_report(report: AuditReport, out_path: Optional[Union[str, Path]] = None) -> Path:
    if out_path is None:
        safe = "".join(c for c in report.company_name if c.isalnum() or c in " -_").strip().replace(" ", "_")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = REPORT_DIR / f"AuditIQ_{safe or 'report'}_{stamp}.pdf"
    out_path = Path(out_path)
    out_path.write_bytes(report_bytes(report))
    return out_path

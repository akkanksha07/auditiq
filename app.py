"""AuditIQ — AI-powered forensic audit intelligence dashboard (Streamlit).

UI: "Aurora v2" — Satoshi typeface, emoji-free (inline-SVG line icons), a split
"show-the-product" landing and a bento, verdict-led dashboard. Presentation only;
all analysis logic lives in the auditiq package and is untouched.
"""
from __future__ import annotations

import os
import re
import sys

import plotly.graph_objects as go
import streamlit as st

# Bridge Streamlit Cloud / secrets.toml secrets into env vars BEFORE importing
# auditiq.config (which reads ANTHROPIC_API_KEY at import time).
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

# Self-heal Streamlit Cloud hot-reloads: after a git-pull update the script re-runs
# from NEW source while previously imported package modules can stay cached in
# sys.modules from the OLD process. If the cached auditiq.models predates the
# forensic layer, purge the package cache so everything re-imports fresh.
import auditiq.models as _aiq_models_check  # noqa: E402

if not hasattr(_aiq_models_check, "ForensicReview"):
    for _k in [k for k in list(sys.modules) if k == "auditiq" or k.startswith("auditiq.")]:
        del sys.modules[_k]
del _aiq_models_check

from auditiq.analysis.benford import EXPECTED, analyze as benford_analyze
from auditiq.analysis.benchmark import industries
from auditiq.analysis.scoring import assess_tiers
from auditiq.config import ALTMAN_ZONES, settings
from auditiq.intelligence.forensic import CATEGORY_LABEL, analyze_disclosures
from auditiq.intelligence.news import get_news_sentiment
from auditiq.intelligence.summary import generate_summary
from auditiq.models import AuditReport, YearAnalysis
from auditiq.pipeline import build_report
from auditiq.sample_data import (
    SAMPLE_INDUSTRY, get_sample_benford_numbers, get_sample_forensic, get_sample_statements,
)

# ─── Palette ──────────────────────────────────────────────────────────────────
ACCENT = "#6366F1"
INK, BODY, MUTED = "#0F172A", "#475467", "#8A90A0"
HAIR, GRID = "#E6E8EC", "#EEF0F4"
GREEN, AMBER, RED, SLATE = "#16A34A", "#D97706", "#DC2626", "#94A3B8"
CAT = ["#6366F1", "#14B8A6", "#8B5CF6", "#0EA5E9"]

RISK_COLOR = {"low": GREEN, "medium": AMBER, "high": RED}
RISK_TEXT = {"low": "LOW RISK", "medium": "ELEVATED RISK", "high": "HIGH RISK"}
FLAG_COLOR = {"ok": GREEN, "medium": AMBER, "high": RED}
SOFT = {
    GREEN: ("#ECFDF3", "#067647", "#ABEFC6"),
    AMBER: ("#FFFAEB", "#B54708", "#FEDF89"),
    RED: ("#FEF3F2", "#B42318", "#FECDCA"),
    ACCENT: ("#EEF0FF", "#4F46E5", "#DADCFE"),
    SLATE: ("#F2F4F7", "#475467", "#E4E7EC"),
}

# ─── Inline line icons (Lucide-style, no emoji) ───────────────────────────────
_ICONS = {
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.6"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "hash": '<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>',
    "bars": '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "info": '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "arrow": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "scale": '<path d="M12 3v18"/><path d="M5 7h14"/><path d="m5 7-3 6a4 4 0 0 0 6 0z"/><path d="m19 7-3 6a4 4 0 0 0 6 0z"/><path d="M7 21h10"/>',
}


def icon(name: str, size: int = 18, color: str = "currentColor", stroke: float = 1.7) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round" style="flex:none;vertical-align:middle">{_ICONS[name]}</svg>')


st.set_page_config(page_title="AuditIQ — Forensic Audit Intelligence",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
      @import url('https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&display=swap');

      html, body, .stApp, [data-testid="stAppViewContainer"],
      [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
      [class^="aiq-"], [class*=" aiq-"],
      h1, h2, h3, h4, h5, h6, p, label, li, a,
      .stButton button, .stDownloadButton button, button[data-baseweb="tab"],
      [data-testid="stMetric"] *, input, textarea, [data-baseweb="select"] {
        font-family: 'Satoshi', system-ui, -apple-system, sans-serif !important; }
      .stApp { background: #F7F8FA; }
      [data-testid="stHeader"] { background: transparent; }
      .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1220px; }
      h1,h2,h3,h4 { color:#0F172A; letter-spacing:-0.02em; font-weight:700; }
      p, span, li, label { color:#475467; }
      .aiq-num { font-variant-numeric: tabular-nums; font-feature-settings:'tnum' 1; }

      /* Sidebar */
      [data-testid="stSidebar"] { background:#FFFFFF; border-right:1px solid #E6E8EC; }
      [data-testid="stSidebar"] .block-container { padding-top:1.4rem; }

      /* Top bar (landing) */
      .aiq-topbar { display:flex; align-items:center; justify-content:space-between;
        padding:2px 2px 18px; border-bottom:1px solid #ECEEF2; margin-bottom:40px; }
      .aiq-brand { display:flex; align-items:center; gap:11px; }
      .aiq-mark { width:34px; height:34px; border-radius:9px;
        background:linear-gradient(135deg,#6366F1,#8B5CF6); color:#fff; font-weight:700;
        font-size:13px; display:flex; align-items:center; justify-content:center;
        box-shadow:0 4px 12px rgba(99,102,241,.32); }
      .aiq-brand .nm { font-weight:700; font-size:16px; color:#0F172A; letter-spacing:-.01em; }
      .aiq-brand .tg { font-size:11px; color:#8A90A0; margin-top:-2px; }
      .aiq-toplink { display:inline-flex; align-items:center; gap:7px; font-size:13.5px;
        font-weight:600; color:#4F46E5; text-decoration:none; }
      .aiq-toplink:hover { color:#4338CA; }

      /* Hero */
      .aiq-eyebrow { display:inline-flex; align-items:center; gap:8px; font-size:12px;
        font-weight:600; letter-spacing:.02em; color:#4F46E5; background:#EEF0FF;
        border:1px solid #DADCFE; padding:5px 13px; border-radius:999px; margin-bottom:22px; }
      .aiq-h1 { font-size:46px; line-height:1.06; font-weight:900; color:#0F172A;
        letter-spacing:-.03em; margin:0 0 18px; }
      .aiq-lead { font-size:17px; line-height:1.6; color:#5B616E; max-width:30em; margin:0 0 24px; }
      .aiq-trust { font-size:12.5px; color:#98A2B3; margin-top:14px; }

      /* Sample-verdict preview (right of hero) */
      .aiq-preview { background:#FFFFFF; border:1px solid #E6E8EC; border-radius:18px;
        box-shadow:0 20px 45px -20px rgba(16,24,40,.22), 0 2px 6px rgba(16,24,40,.05);
        overflow:hidden; }
      .aiq-preview-top { display:flex; align-items:center; justify-content:space-between;
        padding:16px 18px; border-bottom:1px solid #F1F2F5; }
      .aiq-preview-top .co { font-weight:700; color:#0F172A; font-size:15px; }
      .aiq-preview-top .yr { font-size:12px; color:#98A2B3; }
      .aiq-preview-scores { display:grid; grid-template-columns:1fr 1fr; gap:1px;
        background:#F1F2F5; border-bottom:1px solid #F1F2F5; }
      .aiq-preview-scores .s { background:#fff; padding:14px 18px; }
      .aiq-preview-scores .l { font-size:10.5px; text-transform:uppercase; letter-spacing:.06em;
        color:#98A2B3; font-weight:600; }
      .aiq-preview-scores .v { font-size:26px; font-weight:800; letter-spacing:-.02em; margin-top:3px; }
      .aiq-preview-scores .t { font-size:11.5px; color:#8A90A0; margin-top:1px; }
      .aiq-preview-find { padding:12px 18px 16px; display:flex; flex-direction:column; gap:9px; }
      .aiq-preview-find .f { display:flex; gap:9px; align-items:flex-start; font-size:12.5px;
        color:#475467; line-height:1.35; }
      .aiq-preview-find .dot { width:7px; height:7px; border-radius:50%; margin-top:5px; flex:none; }

      /* Checks strip */
      .aiq-strip { display:grid; grid-template-columns:repeat(5,1fr); border:1px solid #E6E8EC;
        border-radius:16px; background:#fff; overflow:hidden; box-shadow:0 1px 2px rgba(16,24,40,.04); }
      .aiq-strip .c { padding:20px 22px; border-right:1px solid #F1F2F5; }
      .aiq-strip .c:last-child { border-right:none; }
      .aiq-strip .ic { width:38px; height:38px; border-radius:10px; background:#EEF0FF; color:#6366F1;
        display:flex; align-items:center; justify-content:center; margin-bottom:12px; }
      .aiq-strip .t { font-weight:700; color:#0F172A; font-size:14px; }
      .aiq-strip .d { font-size:12.5px; color:#8A90A0; margin-top:2px; }

      /* Steps timeline */
      .aiq-steps { display:grid; grid-template-columns:repeat(4,1fr); gap:0; margin-top:6px; }
      .aiq-steps .st { position:relative; padding:0 20px 0 0; }
      .aiq-steps .n { font-size:12px; font-weight:700; color:#6366F1; font-variant-numeric:tabular-nums; }
      .aiq-steps .bar { height:2px; background:#E6E8EC; margin:10px 0 14px; position:relative; }
      .aiq-steps .bar::before { content:''; position:absolute; left:0; top:0; width:22px; height:2px;
        background:#6366F1; }
      .aiq-steps .t { font-weight:700; color:#0F172A; font-size:14.5px; }
      .aiq-steps .d { font-size:12.5px; color:#8A90A0; margin-top:3px; }

      /* Command bar (dashboard) */
      .aiq-co { font-size:26px; font-weight:800; color:#0F172A; letter-spacing:-.02em; line-height:1.1; }
      .aiq-co-meta { font-size:13px; color:#8A90A0; margin-top:3px; }

      /* Bento verdict band */
      .aiq-verdict { background:#FFFFFF; border:1px solid #E6E8EC; border-radius:16px;
        padding:22px 24px; height:100%; box-shadow:0 1px 2px rgba(16,24,40,.04); }
      .aiq-verdict .eb { font-size:11px; text-transform:uppercase; letter-spacing:.08em;
        color:#98A2B3; font-weight:700; }
      .aiq-verdict .risk { font-size:30px; font-weight:900; letter-spacing:-.02em; margin:4px 0 12px; }
      .aiq-verdict .sum { font-size:14.5px; line-height:1.65; color:#3F4654; }
      .aiq-verdict .meta { font-size:12px; color:#98A2B3; margin-top:14px;
        border-top:1px solid #F1F2F5; padding-top:12px; }

      .aiq-score { background:#FFFFFF; border:1px solid #E6E8EC; border-radius:16px;
        padding:16px 18px; box-shadow:0 1px 2px rgba(16,24,40,.04); }
      .aiq-score + .aiq-score { margin-top:14px; }
      .aiq-score .l { font-size:11px; text-transform:uppercase; letter-spacing:.06em;
        color:#98A2B3; font-weight:600; }
      .aiq-score .v { font-size:32px; font-weight:800; letter-spacing:-.02em; line-height:1.05; margin-top:3px; }
      .aiq-score .t { font-size:12.5px; color:#8A90A0; margin-top:3px; }

      /* Compact supporting metrics */
      .aiq-msm { background:#FFFFFF; border:1px solid #E6E8EC; border-radius:13px; padding:13px 16px;
        box-shadow:0 1px 2px rgba(16,24,40,.04); }
      .aiq-msm .l { font-size:10.5px; text-transform:uppercase; letter-spacing:.05em; color:#98A2B3; font-weight:600; }
      .aiq-msm .v { font-size:21px; font-weight:700; letter-spacing:-.01em; margin-top:2px; }
      .aiq-msm .t { font-size:11.5px; color:#98A2B3; margin-top:1px; }

      /* Chips / badges */
      .aiq-chip { display:inline-block; font-size:11px; font-weight:700; padding:3px 11px;
        border-radius:999px; letter-spacing:.02em; }
      .aiq-badge-lg { display:inline-block; font-size:12px; font-weight:700; letter-spacing:.05em;
        padding:6px 15px; border-radius:999px; }

      /* Findings */
      .aiq-finding { background:#FFFFFF; border:1px solid #E6E8EC; border-left:4px solid #94A3B8;
        border-radius:12px; padding:15px 18px; margin-bottom:12px; box-shadow:0 1px 2px rgba(16,24,40,.04); }
      .aiq-finding .hd { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:6px; }
      .aiq-finding .ti { font-size:14.5px; color:#0F172A; font-weight:700; letter-spacing:-.01em; }
      .aiq-finding p { margin:0; font-size:13.5px; color:#475467; line-height:1.6; }
      .aiq-finding .why { margin-top:9px; font-size:13px; color:#475467; line-height:1.55; }
      .aiq-finding .why b { color:#0F172A; }
      .aiq-inno { margin-top:9px; background:#F7F8FA; border:1px solid #EEF0F4; border-radius:9px;
        padding:9px 13px; font-size:12.5px; color:#667085; line-height:1.6; }
      .aiq-inno b { display:block; color:#475467; font-size:10.5px; text-transform:uppercase;
        letter-spacing:.06em; margin-bottom:3px; }
      .aiq-quote { margin:10px 0 0; padding:9px 13px; border-left:3px solid #C7CBD4;
        background:#F7F8FA; border-radius:0 9px 9px 0; font-size:12.5px; color:#475467;
        font-style:italic; line-height:1.55; }
      .aiq-cat { display:inline-block; font-size:10.5px; font-weight:700; letter-spacing:.04em;
        text-transform:uppercase; color:#667085; background:#F2F4F7; border:1px solid #E4E7EC;
        padding:2px 9px; border-radius:5px; margin-right:8px; vertical-align:middle; }

      /* Callouts (replace st alerts) */
      .aiq-callout { display:flex; gap:11px; align-items:flex-start; border-radius:12px;
        padding:13px 16px; font-size:13.5px; line-height:1.55; border:1px solid; margin:2px 0; }
      .aiq-callout .tx { color:inherit; }

      /* Section headings */
      .aiq-h { font-size:19px; font-weight:800; color:#0F172A; letter-spacing:-.02em; margin:8px 0 3px; }
      .aiq-sub { font-size:13.5px; color:#8A90A0; margin-bottom:16px; }
      .aiq-rule { height:1px; background:#ECEEF2; margin:20px 0; border:none; }

      /* Tabs */
      div[data-baseweb="tab-list"] { gap:2px; border-bottom:1px solid #E6E8EC; }
      button[data-baseweb="tab"] { font-weight:600; font-size:14px; color:#667085; padding:9px 15px; }
      button[data-baseweb="tab"]:hover { color:#0F172A; }
      button[data-baseweb="tab"][aria-selected="true"] { color:#6366F1; }
      div[data-baseweb="tab-highlight"] { background-color:#6366F1; height:2.5px; }

      /* Buttons */
      .stButton button, .stDownloadButton button { border-radius:10px; font-weight:700; font-size:14px;
        border:1px solid #E6E8EC; padding:10px 16px; transition:all .15s ease; }
      .stButton button:hover, .stDownloadButton button:hover { border-color:#C7CBD4; }
      .stButton button[kind="primary"] { border:none; box-shadow:0 4px 12px rgba(99,102,241,.28); }
      .stButton button[kind="primary"]:hover { filter:brightness(1.06); }

      /* Uploader */
      [data-testid="stFileUploaderDropzone"] { background:#FFFFFF; border:1.5px dashed #C7CBD4; border-radius:14px; }
      [data-testid="stFileUploaderDropzone"]:hover { border-color:#6366F1; background:#FBFBFF; }

      /* Segmented control (year) */
      [data-testid="stSegmentedControl"] button { font-weight:600; }

      /* st.metric */
      [data-testid="stMetric"] { background:#FFFFFF; border:1px solid #E6E8EC; border-radius:12px;
        padding:14px 16px; box-shadow:0 1px 2px rgba(16,24,40,.04); }
      [data-testid="stMetricLabel"] p { color:#8A90A0; font-size:12px; font-weight:600;
        text-transform:uppercase; letter-spacing:.05em; }
      [data-testid="stExpander"] { border:1px solid #E6E8EC; border-radius:12px; background:#FFFFFF; }
      [data-testid="stExpander"] summary { font-weight:700; color:#0F172A; }
      hr { border-color:#ECEEF2; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Small HTML helpers ───────────────────────────────────────────────────────
def chip(text: str, base: str, size: str = "sm") -> str:
    bg, fg, bd = SOFT.get(base, SOFT[SLATE])
    cls = "aiq-badge-lg" if size == "lg" else "aiq-chip"
    return f'<span class="{cls}" style="background:{bg};color:{fg};border:1px solid {bd}">{text}</span>'


def callout(text: str, kind: str = "info") -> None:
    base = {"info": ACCENT, "warn": AMBER, "good": GREEN, "bad": RED}[kind]
    ic = {"info": "info", "warn": "alert", "good": "check", "bad": "alert"}[kind]
    bg, fg, bd = SOFT[base]
    st.markdown(f'<div class="aiq-callout" style="background:{bg};border-color:{bd};color:{fg}">'
                f'{icon(ic, 17, fg)}<div class="tx">{text}</div></div>', unsafe_allow_html=True)


def section(title: str, sub: str | None = None) -> None:
    html = f'<div class="aiq-h">{title}</div>'
    if sub:
        html += f'<div class="aiq-sub">{sub}</div>'
    st.markdown(html, unsafe_allow_html=True)


def spacer(px: int) -> None:
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)


def style_fig(fig: go.Figure, height: int = 320, title: str | None = None,
              showlegend: bool | None = None) -> go.Figure:
    has_legend = showlegend is not False
    layout = dict(
        height=height, template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=BODY, family="Satoshi, system-ui, sans-serif", size=12),
        # legend sits BELOW the plot so it never collides with the title
        margin=dict(l=8, r=8, t=44 if title else 14, b=54 if has_legend else 14),
        colorway=CAT,
        legend=dict(orientation="h", yanchor="top", y=-0.24, x=0, xanchor="left",
                    font=dict(size=11, color=BODY), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=HAIR, font=dict(color=INK, size=12)),
    )
    if title:
        layout["title"] = dict(text=title, font=dict(size=14.5, color=INK),
                               x=0, xanchor="left", y=0.97, yanchor="top")
    if showlegend is not None:
        layout["showlegend"] = showlegend
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor=GRID, linecolor=HAIR, zerolinecolor=HAIR,
                     tickfont=dict(color=MUTED, size=11), title_font=dict(color=MUTED, size=12))
    fig.update_yaxes(gridcolor=GRID, linecolor=HAIR, zerolinecolor=HAIR,
                     tickfont=dict(color=MUTED, size=11), title_font=dict(color=MUTED, size=12))
    return fig


def _guess_year(name: str) -> str:
    m = re.search(r"(20\d{2})", name)
    return m.group(1) if m else name.rsplit(".", 1)[0][:12]


def _beneish_color(b) -> str:
    if b is None:
        return SLATE
    if b.is_manipulator:
        return RED
    return AMBER if b.m_score > b.threshold - 0.5 else GREEN


# ─── Analysis pipeline (logic unchanged) ──────────────────────────────────────
def run_analysis(files, industry: str) -> AuditReport:
    from auditiq.extraction.ai_extractor import extract_financials
    from auditiq.extraction.pdf_reader import read_pdf_bytes

    statements, benford_texts, forensic_text = [], {}, ""
    with st.status("Running forensic analysis…", expanded=True) as status:
        for f in files:
            yr = _guess_year(f.name)
            st.write(f"Reading {f.name}")
            # Deep read — the auditor's report and notes often sit far past page 60.
            content = read_pdf_bytes(f.getvalue(), max_pages=settings.forensic_max_pdf_pages)
            st.write(f"Extracting financials with Claude "
                     f"(scanned {content.scanned_pages} of {content.num_pages} pages)…")
            fs = extract_financials(content.financial_text, year_label=yr)
            statements.append(fs)
            benford_texts[fs.year or yr] = content.full_text
            forensic_text = content.full_text  # latest file read feeds the disclosure review

        st.write("Scoring — Beneish, Altman, Benford, benchmarking…")
        company = next((s.company_name for s in statements if s.company_name), None)
        news = None
        if company:
            st.write("Cross-referencing recent news sentiment…")
            news = get_news_sentiment(company)
        report = build_report(statements, industry=industry, benford_texts=benford_texts, news=news)
        st.write("Reviewing the auditor's report, notes and MD&A for disclosure red flags…")
        report.forensic = analyze_disclosures(forensic_text, company)
        if report.years:
            st.write("Writing the audit summary…")
            report.summary = generate_summary(report.years[-1], industry)
        status.update(label="Analysis complete", state="complete")
    return report


def load_sample() -> AuditReport:
    report = build_report(get_sample_statements(), industry=SAMPLE_INDUSTRY)
    if report.years:
        report.years[-1].benford = benford_analyze(get_sample_benford_numbers())
    report.forensic = get_sample_forensic()
    return report


# ─── Sidebar ──────────────────────────────────────────────────────────────────
def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            f'<div class="aiq-brand"><div class="aiq-mark">AI</div>'
            f'<div><div class="nm">AuditIQ</div><div class="tg">Forensic audit intelligence</div></div></div>',
            unsafe_allow_html=True)
        spacer(14)

        ind_items = industries()
        keys = [k for k, _ in ind_items]
        labels = {k: lbl for k, lbl in ind_items}
        default = st.session_state.get("industry", "retail")
        industry = st.selectbox("Industry (for benchmarking)", keys,
                                index=keys.index(default) if default in keys else 0,
                                format_func=lambda k: labels[k])
        st.session_state["industry"] = industry

        spacer(8)
        if settings.has_api_key:
            callout("Claude API connected.", "good")
        else:
            callout("No API key — AI extraction & news are disabled. Load sample data to explore.", "warn")
        st.caption(f"Model: `{settings.extraction_model}`")

        spacer(10)
        if st.button("Load sample data", use_container_width=True, type="primary"):
            st.session_state["report"] = load_sample()
            st.session_state.pop("view", None)
            st.rerun()
        if st.session_state.get("report") and st.button("Clear", use_container_width=True):
            st.session_state.pop("report", None)
            st.session_state.pop("view", None)
            st.rerun()
        spacer(6)
        if st.button("Validation · back-test", use_container_width=True):
            st.session_state["view"] = "validation"
            st.rerun()
    return industry


# ─── Landing ──────────────────────────────────────────────────────────────────
def topbar() -> None:
    st.markdown(
        f'<div class="aiq-topbar"><div class="aiq-brand"><div class="aiq-mark">AI</div>'
        f'<div><div class="nm">AuditIQ</div><div class="tg">Forensic audit intelligence</div></div></div>'
        f'<a class="aiq-toplink" href="#glossary">{icon("info", 15)} How it works</a></div>',
        unsafe_allow_html=True)


def _preview_card() -> str:
    def line(color, text):
        return f'<div class="f"><span class="dot" style="background:{color}"></span>{text}</div>'
    return (
        '<div class="aiq-preview"><div class="aiq-preview-top">'
        '<div><div class="co">Tesco PLC</div><div class="yr">Annual report · 2023</div></div>'
        f'{chip("3 RED FLAGS", RED)}</div>'
        '<div class="aiq-preview-scores">'
        f'<div class="s"><div class="l">Beneish M-Score</div><div class="v aiq-num" style="color:{RED}">−1.84</div>'
        '<div class="t">Manipulator zone</div></div>'
        f'<div class="s"><div class="l">Altman Z-Score</div><div class="v aiq-num" style="color:{AMBER}">2.10</div>'
        '<div class="t">Grey zone</div></div></div>'
        '<div class="aiq-preview-find">'
        f'{line(RED, "Receivables growing faster than revenue")}'
        f'{line(AMBER, "Gross margin below the sector average")}'
        f'{line(RED, "Net income not backed by operating cash")}'
        '</div></div>')


def upload_view(industry: str) -> None:
    topbar()
    left, right = st.columns([1.04, 0.96], gap="large")
    with left:
        st.markdown(
            f'<div class="aiq-eyebrow">{icon("search", 14, "#6366F1")} AI-powered forensic screening</div>'
            '<div class="aiq-h1">Read the numbers<br>behind the numbers.</div>'
            '<div class="aiq-lead">Upload an annual report and AuditIQ screens it for earnings '
            "manipulation, bankruptcy risk and digit anomalies — then reads the auditor's report "
            'and notes for disclosure red flags. Indicators to investigate, never verdicts.</div>',
            unsafe_allow_html=True)
        files = st.file_uploader("Annual report PDFs — up to 3 years", type="pdf",
                                 accept_multiple_files=True)
        disabled = not settings.has_api_key
        if st.button("Run analysis", type="primary", disabled=disabled, use_container_width=True):
            if not files:
                callout("Please upload at least one PDF.", "bad")
            elif len(files) > 3:
                callout("Please upload at most 3 reports.", "bad")
            else:
                try:
                    st.session_state["report"] = run_analysis(files, industry)
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    callout(f"Analysis failed: {exc}", "bad")
        if disabled:
            callout("Add ANTHROPIC_API_KEY to analyse PDFs — or load sample data from the sidebar.", "info")
        st.markdown('<div class="aiq-trust">Not a substitute for qualified audit advice · '
                    'runs the same models used in external audit.</div>', unsafe_allow_html=True)
    with right:
        st.markdown(_preview_card(), unsafe_allow_html=True)

    st.markdown('<hr class="aiq-rule">', unsafe_allow_html=True)
    checks = [
        ("target", "Beneish M-Score", "Earnings-manipulation screen"),
        ("activity", "Altman Z-Score", "Bankruptcy-risk screen"),
        ("hash", "Benford's Law", "Digit-anomaly screen"),
        ("bars", "Benchmarking", "Ratios vs the sector"),
        ("file", "Disclosure review", "Auditor's report & notes"),
    ]
    cells = "".join(
        f'<div class="c"><div class="ic">{icon(ic, 19)}</div><div class="t">{t}</div>'
        f'<div class="d">{d}</div></div>' for ic, t, d in checks)
    st.markdown(f'<div class="aiq-strip">{cells}</div>', unsafe_allow_html=True)

    spacer(34)
    section("From PDF to verdict in four steps")
    steps = [("01", "Upload the report", "Any annual report PDF, up to three years."),
             ("02", "Extract the figures", "Claude reads the statements into structured data."),
             ("03", "Run the checks", "Four forensic models score and benchmark the company."),
             ("04", "Review & export", "An interactive dashboard and a shareable PDF.")]
    st.markdown('<div class="aiq-steps">' + "".join(
        f'<div class="st"><div class="n">{n}</div><div class="bar"></div>'
        f'<div class="t">{t}</div><div class="d">{d}</div></div>' for n, t, d in steps) + '</div>',
        unsafe_allow_html=True)

    spacer(40)
    st.markdown('<span id="glossary"></span>', unsafe_allow_html=True)
    section("Understanding the output", "What each score and ratio means, in plain English.")
    render_guide()


# ─── Guide / glossary (landing + dashboard tab) ───────────────────────────────
def render_guide() -> None:
    with st.expander("Beneish M-Score — an earnings lie-detector", expanded=False):
        st.markdown(
            "**What it is.** Eight financial ratios combined into a single score that estimates the "
            "probability a company has **manipulated its earnings**.\n\n"
            "**How to read it.** A score **above −1.78** places the company in the *manipulator zone*. "
            "The eight indices (DSRI, GMI, AQI, SGI, DEPI, SGAI, TATA, LVGI) capture signals like "
            "receivables growing faster than revenue, or profit that isn't backed by cash.\n\n"
            "**Rule of thumb.** Higher = riskier; elevated components are the drivers.")
    with st.expander("Altman Z-Score — a bankruptcy thermometer"):
        st.markdown(
            "**What it is.** A model blending solvency and profitability into one number that sorts a "
            "company into **Safe**, **Grey**, or **Distress**.\n\n"
            "**How to read it.** Higher is healthier. Thresholds depend on the model variant "
            "(manufacturing, private, or emerging-market); the app selects the right one and shows the "
            "bands under the gauge.\n\n**Rule of thumb.** In the **distress** zone → material going-concern risk.")
    with st.expander("Benford's Law — do the digits look natural?"):
        st.markdown(
            "**What it is.** In genuine accounting data, leading digits follow a predictable curve — "
            "numbers start with **1 about 30%** of the time and with **9 under 5%**.\n\n"
            "**How to read it.** AuditIQ compares the report's actual first-digit distribution against "
            "that curve. Large deviations (a high **MAD** or a significant **chi-square**) can indicate "
            "rounding, estimation, or fabricated figures. Needs a large sample to be reliable.\n\n"
            "**Rule of thumb.** *Close/acceptable* = normal; *nonconformity* = worth a look.")
    with st.expander("The key financial ratios"):
        st.markdown(
            "- **Gross margin** — profit kept per £ of sales; falling margins pressure management.\n"
            "- **Current ratio** — short-term assets ÷ short-term bills; **below 1.0** is a liquidity flag.\n"
            "- **Receivables days** — how long customers take to pay; rising fast = revenue-quality risk.\n"
            "- **Debt / equity** — leverage; higher than the sector = more financial risk.\n"
            "- **Interest coverage** — profit ÷ interest; **below ~2×** = debt-service strain.\n"
            "- **Asset turnover** — sales per £ of assets; low vs peers = inefficiency.")
    with st.expander("The disclosure review — reading the report's own words"):
        st.markdown(
            "**What it is.** Claude reads the independent auditor's report, key audit matters, "
            "the notes, and management's discussion, and surfaces the disclosure red flags "
            "forensic accountants check first: going-concern language, restatements, "
            "internal-control weaknesses, auditor or CFO changes, related-party transactions, "
            "revenue-recognition changes, and heavy reliance on adjusted (non-GAAP) measures.\n\n"
            "**How to read it.** Every flag carries a **verbatim quote** from the report — "
            "verify it against the source. These are leads for investigation, not conclusions.")
    with st.expander("How the headline screening result is decided"):
        st.markdown(
            "Every check contributes **red flags**, each rated *low / medium / high*. The headline "
            "is a **count of flags to investigate**, coloured by the worst severity present — a "
            "screening summary, not a verdict. Benchmark deviations are graded against the "
            "selected industry, so a value always appears in context (e.g. *94 days vs a sector "
            "average of 61*).")
    st.caption("AuditIQ is an analytical screening tool, not a substitute for qualified audit advice. "
               "All scores are model estimates and must be reviewed by a professional.")


# ─── Dashboard ────────────────────────────────────────────────────────────────
def _verdict_card(report: AuditReport, year: YearAnalysis) -> str:
    disc = report.forensic.flags if report.forensic else []
    ta = assess_tiers(year.findings, disc)
    color = RISK_COLOR[ta.level] if ta.substantive else GREEN
    headline = (f"{ta.substantive} substantive red flag{'s' if ta.substantive != 1 else ''}"
                if ta.substantive else "No substantive red flags")
    summary = (report.summary or "").strip()
    if not summary:
        lead = "; ".join(ta.top)
        ctx = (f" {ta.context} peer-context observation{'s' if ta.context != 1 else ''} are shown "
               f"separately and are not treated as fraud signals." if ta.context else "")
        summary = (f"Weighted by forensic signal strength: {ta.t1} earnings-quality/distress and "
                   f"{ta.t2} disclosure flag{'s' if ta.t2 != 1 else ''} for {year.year}."
                   + (f" Start with: {lead}." if lead else "") + ctx)
    return (f'<div class="aiq-verdict"><div class="eb">Screening result · weighted by signal strength</div>'
            f'<div class="risk" style="color:{color}">{headline}</div>'
            f'<div class="sum">{summary}</div>'
            f'<div class="meta">Tier 1 {ta.t1} · Tier 2 {ta.t2} · Tier 3 (context) {ta.t3} · '
            f'{report.industry.title()} · {", ".join(y.year for y in report.years)}</div></div>')


def _score_card(label: str, value: str, sub: str, color: str) -> str:
    return (f'<div class="aiq-score"><div class="l">{label}</div>'
            f'<div class="v aiq-num" style="color:{color}">{value}</div>'
            f'<div class="t">{sub}</div></div>')


def _metric_sm(label: str, value: str, sub: str, color: str) -> str:
    return (f'<div class="aiq-msm"><div class="l">{label}</div>'
            f'<div class="v aiq-num" style="color:{color}">{value}</div>'
            f'<div class="t">{sub}</div></div>')


def findings_tab(year: YearAnalysis) -> None:
    section("Quantitative red flags",
            f"{len(year.findings)} raised for {year.year}, most severe first — each is a screen "
            f"to investigate, not a conclusion.")
    for f in year.findings:
        bg, fg, bd = SOFT[RISK_COLOR[f.level]]
        why = f'<div class="why"><b>Why it flagged.</b> {f.why}</div>' if f.why else ""
        inno = ""
        if f.innocent:
            items = "".join(f"<div>– {i}</div>" for i in f.innocent)
            inno = f'<div class="aiq-inno"><b>Common innocent explanations</b>{items}</div>'
        st.markdown(
            f'<div class="aiq-finding" style="border-left-color:{RISK_COLOR[f.level]}">'
            f'<div class="hd"><span class="ti">{f.title}</span>'
            f'<span class="aiq-chip" style="background:{bg};color:{fg};border:1px solid {bd}">'
            f'{f.level.upper()}</span></div><p>{f.body}</p>{why}{inno}</div>',
            unsafe_allow_html=True)


def forensic_tab(report: AuditReport) -> None:
    fr = report.forensic
    if fr is None:
        callout("The disclosure review reads the auditor's report, key audit matters, notes and "
                "MD&A from an uploaded PDF. It requires the Claude API — upload a report with an "
                "API key configured. (Demo mode shows an illustrative sample.)", "info")
        return
    section("Disclosure-level red flags",
            "What the report's own words say — auditor's report, key audit matters, notes and "
            "MD&A. Every flag carries a verbatim quote so it can be verified against the source.")
    if fr.summary:
        callout(fr.summary, "info")
    if fr.sections_reviewed:
        st.caption("Sections located: " + " · ".join(fr.sections_reviewed))
    if not fr.flags:
        callout("No disclosure-level red flags were identified in the sections reviewed. "
                "A clean disclosure read is a good sign — not a guarantee.", "good")
        return
    for fl in fr.flags:
        base = RISK_COLOR[fl.severity]
        bg, fg, bd = SOFT[base]
        quote = f'<div class="aiq-quote">“{fl.evidence}”</div>' if fl.evidence else ""
        loc = (f' <span style="color:#98A2B3;font-size:11.5px">({fl.location})</span>'
               if fl.location else "")
        why = f'<div class="why"><b>Why it matters.</b> {fl.why}</div>' if fl.why else ""
        inno = ""
        if fl.innocent:
            items = "".join(f"<div>– {i}</div>" for i in fl.innocent)
            inno = f'<div class="aiq-inno"><b>Common innocent explanations</b>{items}</div>'
        st.markdown(
            f'<div class="aiq-finding" style="border-left-color:{base}">'
            f'<div class="hd"><span class="ti"><span class="aiq-cat">'
            f'{CATEGORY_LABEL.get(fl.category, fl.category)}</span>{fl.title}{loc}</span>'
            f'<span class="aiq-chip" style="background:{bg};color:{fg};border:1px solid {bd}">'
            f'{fl.severity.upper()}</span></div>'
            f'<p>{fl.detail}</p>{quote}{why}{inno}</div>', unsafe_allow_html=True)
    st.caption("Automated read of the report's disclosures — verify each quote against the "
               "source document before relying on it.")


def beneish_tab(year: YearAnalysis) -> None:
    from auditiq.analysis.beneish import COMPONENT_INFO
    b = year.beneish
    if not b:
        callout("The Beneish M-Score needs two consecutive years. Upload a prior year to compute it.", "info")
        return
    zone = "manipulator zone" if b.is_manipulator else "non-manipulator zone"
    section("Beneish M-Score components",
            f"Eight indices combine into the M-Score. Score {b.m_score} vs threshold {b.threshold} → {zone}.")
    keys = list(b.components)
    vals = [b.components[k] for k in keys]
    thresh = [COMPONENT_INFO.get(k, (k, '', 1))[2] for k in keys]
    bar_colors = [AMBER if v > t else ACCENT for v, t in zip(vals, thresh)]
    fig = go.Figure(go.Bar(x=keys, y=vals, marker_color=bar_colors, marker_line_width=0,
                           text=[f"{v:g}" for v in vals], textposition="outside",
                           textfont=dict(color=BODY, size=11),
                           hovertemplate="%{x}: %{y:.3f}<extra></extra>"))
    st.plotly_chart(style_fig(fig, height=330, title="Component indices (amber = elevated)",
                              showlegend=False), use_container_width=True)
    for k in keys:
        name, tip, t = COMPONENT_INFO.get(k, (k, "", 1))
        col = AMBER if b.components[k] > t else GREEN
        st.markdown(
            f'<span class="aiq-num" style="color:{col};font-weight:700">{k} {b.components[k]:g}</span> '
            f'<span style="color:#98A2B3">·</span> <b style="color:#0F172A">{name}</b> — '
            f'<span style="color:#667085">{tip}</span>', unsafe_allow_html=True)


def benford_tab(year: YearAnalysis) -> None:
    bf = year.benford
    if not bf or not bf.n:
        callout("Benford's Law runs on the full numeric population of an uploaded PDF. "
                "Not available for this view.", "info")
        return
    digits = [d.digit for d in bf.digits]
    fig = go.Figure()
    fig.add_bar(x=digits, y=[d.observed_pct for d in bf.digits], name="Observed",
                marker_color=ACCENT, marker_line_width=0,
                hovertemplate="Digit %{x}: %{y:.1f}%<extra>Observed</extra>")
    fig.add_scatter(x=digits, y=[round(EXPECTED[d]*100, 2) for d in digits], name="Benford expected",
                    mode="lines+markers", line=dict(color=INK, dash="dot", width=2),
                    marker=dict(size=7, color=INK),
                    hovertemplate="Digit %{x}: %{y:.1f}%<extra>Expected</extra>")
    fig.update_layout(xaxis_title="Leading digit", yaxis_title="% of values")
    st.plotly_chart(style_fig(fig, height=340, title=f"First-digit distribution (n = {bf.n})"),
                    use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Conformity", bf.conformity.title())
    c2.metric("MAD", f"{bf.mad}")
    c3.metric("Chi² (p-value)", f"{bf.chi_square} ({bf.p_value})")
    if bf.note:
        st.caption(bf.note)
    elif bf.suspicious:
        callout("Digit distribution deviates from Benford's Law — possible rounding or fabrication.", "warn")
    else:
        callout("Digit distribution is broadly consistent with Benford's Law.", "good")


def altman_tab(year: YearAnalysis) -> None:
    a = year.altman
    if not a:
        callout("Altman Z-Score needs balance-sheet detail (assets, liabilities, equity).", "info")
        return
    zones = ALTMAN_ZONES.get(a.model_used, ALTMAN_ZONES["original"])
    distress, safe = zones["distress"], zones["safe"]
    top = max(safe + 1, a.z_score + 1)
    section("Altman Z-Score", f"Bankruptcy-risk model ({a.model_used}). "
            f"Distress < {distress} · grey {distress}–{safe} · safe > {safe}.")
    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=a.z_score, title={"text": ""},
            number=dict(font=dict(color=INK, size=40, family="Satoshi")),
            gauge={"axis": {"range": [0, top], "tickcolor": MUTED, "tickfont": {"color": MUTED, "size": 10}},
                   "bar": {"color": RISK_COLOR[a.zone], "thickness": 0.28},
                   "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
                   "steps": [{"range": [0, distress], "color": "rgba(220,38,38,0.14)"},
                             {"range": [distress, safe], "color": "rgba(217,119,6,0.14)"},
                             {"range": [safe, top], "color": "rgba(22,163,74,0.14)"}]}))
        st.plotly_chart(style_fig(fig, height=280), use_container_width=True)
    with right:
        spacer(24)
        st.markdown(chip(a.zone_label.upper() + " ZONE", RISK_COLOR[a.zone], "lg"), unsafe_allow_html=True)
        spacer(6)
        for k, v in a.components.items():
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
                f'border-bottom:1px solid #EEF0F4"><span style="color:#667085;font-size:13px">{k}</span>'
                f'<span class="aiq-num" style="color:#0F172A;font-weight:700;font-size:13px">{v}</span></div>',
                unsafe_allow_html=True)


def benchmark_tab(year: YearAnalysis) -> None:
    rows = year.benchmarks
    if not rows:
        callout("No benchmark data.", "info")
        return
    section("Company vs industry", "Key ratios against the sector average.")
    labels = [r.label for r in rows]
    fig = go.Figure()
    fig.add_bar(y=labels, x=[r.company or 0 for r in rows], name="Company", orientation="h",
                marker_color=ACCENT, marker_line_width=0, hovertemplate="%{y}: %{x}<extra>Company</extra>")
    fig.add_bar(y=labels, x=[r.industry for r in rows], name="Industry", orientation="h",
                marker_color=SLATE, marker_line_width=0, hovertemplate="%{y}: %{x}<extra>Industry</extra>")
    fig.update_layout(barmode="group", yaxis=dict(autorange="reversed"))
    st.plotly_chart(style_fig(fig, height=380), use_container_width=True)
    import pandas as pd
    df = pd.DataFrame([{
        "Metric": r.label, "Company": "N/A" if r.company is None else f"{r.company}{r.unit}",
        "Industry": f"{r.industry}{r.unit}", "Status": r.flag.upper(),
    } for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True)


def trends_tab(report: AuditReport) -> None:
    comp = report.comparison
    if not comp or len(comp.points) < 2:
        callout("Upload 2–3 years to unlock trend analysis.", "info")
        return
    yrs = [p.year for p in comp.points]
    dir_base = {"worsening": RED, "improving": GREEN}.get(comp.direction, SLATE)
    section("Multi-year trend")
    st.markdown("Direction of travel " + chip(comp.direction.title(), dir_base), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_bar(x=yrs, y=[p.revenue for p in comp.points], name="Revenue",
                    marker_color=CAT[0], marker_line_width=0)
        fig.add_bar(x=yrs, y=[p.net_income for p in comp.points], name="Net income",
                    marker_color=CAT[1], marker_line_width=0)
        fig.update_layout(barmode="group")
        st.plotly_chart(style_fig(fig, height=300, title="Revenue & net income"), use_container_width=True)
    with c2:
        fig = go.Figure()
        fig.add_scatter(x=yrs, y=[p.m_score for p in comp.points], name="M-Score",
                        mode="lines+markers", line=dict(color=ACCENT, width=2.5),
                        marker=dict(size=8, color=ACCENT))
        fig.add_scatter(x=yrs, y=[-1.78]*len(yrs), name="Threshold (−1.78)",
                        mode="lines", line=dict(color=RED, dash="dot", width=1.5))
        st.plotly_chart(style_fig(fig, height=300, title="Beneish M-Score over time"), use_container_width=True)
    for n in comp.notes:
        st.markdown(f'<span style="color:#98A2B3">•</span> {n}', unsafe_allow_html=True)


def news_tab(report: AuditReport) -> None:
    n = report.news
    if not n:
        callout("News sentiment requires the Claude API with web search. It runs automatically on "
                "uploaded reports when a company name is detected.", "info")
        return
    base = RED if n.score < -0.15 else GREEN if n.score > 0.15 else AMBER
    left, right = st.columns([1, 2])
    with left:
        st.markdown(_metric_sm("News sentiment", n.label, f"score {n.score:+.2f} · {n.as_of}", base),
                    unsafe_allow_html=True)
    with right:
        st.markdown(f'<b style="color:#0F172A">Summary.</b> '
                    f'<span style="color:#475467">{n.summary}</span>', unsafe_allow_html=True)
        if n.flags:
            st.markdown(" ".join(chip(f, AMBER) for f in n.flags), unsafe_allow_html=True)
    if n.articles:
        spacer(6)
        section("Recent coverage")
        for art in n.articles:
            src = f" · {art.source}" if art.source else ""
            link = f"[{art.title}]({art.url})" if art.url else art.title
            st.markdown(f'{link}<span style="color:#98A2B3;font-size:12.5px">{src} '
                        f'({art.date or "n/a"})</span>', unsafe_allow_html=True)


def report_tab(report: AuditReport) -> None:
    section("Export", "Generate a professional, shareable PDF of the full analysis.")
    if st.button("Generate PDF report", type="primary"):
        from auditiq.reporting.pdf_report import report_bytes
        with st.spinner("Building report…"):
            data = report_bytes(report)
        st.download_button("Download report", data=data,
                           file_name=f"AuditIQ_{report.company_name.replace(' ', '_')}.pdf",
                           mime="application/pdf")
        callout("Report ready.", "good")


def results_view(report: AuditReport) -> None:
    yrs = [y.year for y in report.years]
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f'<div class="aiq-co">{report.company_name}</div>'
                    f'<div class="aiq-co-meta">{report.industry.title()} · forensic screening</div>',
                    unsafe_allow_html=True)
    with c2:
        if len(yrs) > 1:
            sel = st.segmented_control("Year", yrs, default=yrs[-1],
                                       label_visibility="collapsed") or yrs[-1]
        else:
            sel = yrs[0]
    year = next(y for y in report.years if y.year == sel)
    st.markdown('<hr class="aiq-rule">', unsafe_allow_html=True)
    callout("Automated screening on published, audited figures — these are red flags "
            "warranting investigation, not conclusions of manipulation or fraud.", "info")
    spacer(8)

    # Bento verdict band
    v1, v2 = st.columns([1.7, 1], gap="medium")
    with v1:
        st.markdown(_verdict_card(report, year), unsafe_allow_html=True)
    with v2:
        b, a = year.beneish, year.altman
        st.markdown(_score_card("Beneish M-Score", f"{b.m_score}" if b else "—",
                                ("Above screening threshold — flag raised" if b.is_manipulator
                                 else "Below screening threshold")
                                if b else "Needs 2 years", _beneish_color(b)), unsafe_allow_html=True)
        st.markdown(_score_card("Altman Z-Score", f"{a.z_score}" if a else "—",
                                f"{a.zone_label} zone (screen)" if a else "Insufficient data",
                                RISK_COLOR[a.zone] if a else MUTED), unsafe_allow_html=True)

    spacer(14)
    r = year.ratios
    b = year.beneish
    gm, cr, rd = r.gross_margin, r.current_ratio, r.receivables_days
    gm_c = RED if gm is not None and gm < 0.2 else AMBER if gm is not None and gm < 0.35 else GREEN
    cr_c = RED if cr is not None and cr < 1 else AMBER if cr is not None and cr < 1.5 else GREEN
    rd_c = RED if rd is not None and rd > 90 else AMBER if rd is not None and rd > 60 else GREEN
    m = st.columns(4)
    m[0].markdown(_metric_sm("Manipulation screen", f"{b.probability}%" if b else "—",
                             "Probit score — not a fraud probability", _beneish_color(b)),
                  unsafe_allow_html=True)
    m[1].markdown(_metric_sm("Gross margin", f"{gm*100:.1f}%" if gm is not None else "—",
                             "Profitability", gm_c), unsafe_allow_html=True)
    m[2].markdown(_metric_sm("Current ratio", f"{cr}x" if cr is not None else "—",
                             "Liquidity", cr_c), unsafe_allow_html=True)
    m[3].markdown(_metric_sm("Receivables days", f"{rd:.0f}d" if rd is not None else "—",
                             "Collection speed", rd_c), unsafe_allow_html=True)

    spacer(16)
    tabs = st.tabs(["Findings", "Forensic review", "Beneish", "Benford", "Altman",
                    "Benchmarking", "Trends", "News", "Report", "How it works"])
    with tabs[0]:
        findings_tab(year)
    with tabs[1]:
        forensic_tab(report)
    with tabs[2]:
        beneish_tab(year)
    with tabs[3]:
        benford_tab(year)
    with tabs[4]:
        altman_tab(year)
    with tabs[5]:
        benchmark_tab(year)
    with tabs[6]:
        trends_tab(report)
    with tabs[7]:
        news_tab(report)
    with tabs[8]:
        report_tab(report)
    with tabs[9]:
        render_guide()


def _confusion_html(m) -> str:
    def cell(cls, label, val, sub):
        return (f'<div class="cm-cell {cls}"><div class="cm-l">{label}</div>'
                f'<div class="cm-v aiq-num">{val}</div><div class="cm-s">{sub}</div></div>')
    return ('<div class="aiq-cm">'
            '<div></div><div class="cm-top">Screen: FLAG</div><div class="cm-top">Screen: clear</div>'
            '<div class="cm-side">Actual:<br>manipulator</div>'
            + cell("tp", "True positive", m.tp, "fraud caught")
            + cell("fn", "False negative", m.fn, "fraud missed")
            + '<div class="cm-side">Actual:<br>clean</div>'
            + cell("fp", "False positive", m.fp, "clean flagged")
            + cell("tn", "True negative", m.tn, "clean cleared")
            + '</div>')


def validation_view() -> None:
    from auditiq.analysis.backtest import run_backtest
    import pandas as pd

    st.markdown(
        """<style>
          .aiq-cm { display:grid; grid-template-columns:auto 1fr 1fr; gap:8px; align-items:stretch; }
          .aiq-cm .cm-top { font-size:10.5px; font-weight:700; color:#667085; text-transform:uppercase;
            letter-spacing:.05em; text-align:center; align-self:end; padding-bottom:5px; }
          .aiq-cm .cm-side { font-size:10.5px; font-weight:700; color:#667085; align-self:center;
            line-height:1.25; max-width:78px; }
          .aiq-cm .cm-cell { border-radius:12px; padding:14px 10px; text-align:center; border:1px solid; }
          .aiq-cm .cm-cell.tp { background:#ECFDF3; border-color:#ABEFC6; }
          .aiq-cm .cm-cell.tn { background:#F0FDF9; border-color:#A7F3D0; }
          .aiq-cm .cm-cell.fn { background:#FEF3F2; border-color:#FECDCA; }
          .aiq-cm .cm-cell.fp { background:#FFFAEB; border-color:#FEDF89; }
          .aiq-cm .cm-l { font-size:10px; text-transform:uppercase; letter-spacing:.04em; color:#667085; font-weight:700; }
          .aiq-cm .cm-v { font-size:30px; font-weight:800; color:#0F172A; line-height:1.1; }
          .aiq-cm .cm-s { font-size:11px; color:#8A90A0; }
        </style>""", unsafe_allow_html=True)

    if st.button("← Back to analysis"):
        st.session_state.pop("view", None)
        st.rerun()

    res = run_backtest()
    st.markdown('<div class="aiq-co">Validation — does it actually work?</div>'
                '<div class="aiq-co-meta">Every screen run over known accounting scandals versus '
                'matched clean peers.</div>', unsafe_allow_html=True)
    st.markdown('<hr class="aiq-rule">', unsafe_allow_html=True)
    callout("This is a screen, not a detector. Below is its <b>measured</b> hit-rate and "
            "false-positive rate on a labelled set — the honest picture of what it catches and "
            "misses, and why a clean outlier like Apple is <b>not</b> flagged while Enron is.", "info")
    spacer(8)

    tiered = next(s for s in res.screens if s.name.startswith("Tiered"))
    m = tiered.matrix
    left, right = st.columns([1, 1], gap="large")
    with left:
        section("Confusion matrix — tiered screen",
                f"{res.n_manipulators} manipulators · {res.n_clean} clean peers")
        st.markdown(_confusion_html(m), unsafe_allow_html=True)
    with right:
        section("Headline metrics")
        c = st.columns(3)
        c[0].markdown(_metric_sm("Hit-rate", f"{m.sensitivity*100:.0f}%",
                                 "sensitivity · frauds caught", GREEN if m.sensitivity >= 0.5 else AMBER),
                      unsafe_allow_html=True)
        c[1].markdown(_metric_sm("False alarms", f"{m.false_positive_rate*100:.0f}%",
                                 "false-positive rate", GREEN if m.false_positive_rate <= 0.15 else AMBER),
                      unsafe_allow_html=True)
        c[2].markdown(_metric_sm("Accuracy", f"{m.accuracy*100:.0f}%", "overall", ACCENT),
                      unsafe_allow_html=True)
        spacer(12)
        st.markdown("**Per-screen performance**")
        st.dataframe(pd.DataFrame([{
            "Screen": s.name,
            "Sensitivity": f"{s.matrix.sensitivity*100:.0f}%",
            "FPR": f"{s.matrix.false_positive_rate*100:.0f}%",
            "Accuracy": f"{s.matrix.accuracy*100:.0f}%",
            "TP/FP/TN/FN": f"{s.matrix.tp}/{s.matrix.fp}/{s.matrix.tn}/{s.matrix.fn}",
        } for s in res.screens]), use_container_width=True, hide_index=True)

    spacer(16)
    section("Case by case", "The tiered screen's call for every company.")

    def _result(r):
        if r.is_manipulator and r.tiered_flag:
            return "caught"
        if r.is_manipulator:
            return "missed"
        return "false alarm" if r.tiered_flag else "correct"

    st.dataframe(pd.DataFrame([{
        "Company": r.company, "Actual": "Manipulator" if r.is_manipulator else "Clean",
        "Sector": r.sector.title(),
        "M-Score": r.m_score, "Z-Score": r.z_score, "Altman": r.altman_zone or "—",
        "Screen call": "FLAG" if r.tiered_flag else "clear", "Outcome": _result(r),
    } for r in res.rows]), use_container_width=True, hide_index=True)

    spacer(8)
    for cav in res.caveats:
        st.caption("— " + cav)


def main() -> None:
    industry = sidebar()
    if st.session_state.get("view") == "validation":
        validation_view()
        return
    report = st.session_state.get("report")
    if report is None:
        upload_view(industry)
    else:
        results_view(report)


if __name__ == "__main__":
    main()

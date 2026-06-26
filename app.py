"""AuditIQ — AI-powered forensic audit intelligence dashboard (Streamlit)."""
from __future__ import annotations

import os
import re

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

from auditiq.analysis.benford import EXPECTED, analyze as benford_analyze
from auditiq.analysis.benchmark import industries
from auditiq.config import ALTMAN_ZONES, settings
from auditiq.intelligence.news import get_news_sentiment
from auditiq.intelligence.summary import generate_summary
from auditiq.models import AuditReport, YearAnalysis
from auditiq.pipeline import build_report
from auditiq.sample_data import (
    SAMPLE_INDUSTRY, get_sample_benford_numbers, get_sample_statements,
)

# ─── Palette ──────────────────────────────────────────────────────────────────
ACCENT, GREEN, AMBER, RED, GREY = "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#64748b"
RISK_COLOR = {"low": GREEN, "medium": AMBER, "high": RED}
RISK_TEXT = {"low": "LOW RISK", "medium": "ELEVATED RISK", "high": "HIGH RISK"}
FLAG_COLOR = {"ok": GREEN, "medium": AMBER, "high": RED}
PLOTLY_BG = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                 font=dict(color="#94a3b8", family="IBM Plex Mono"),
                 margin=dict(l=10, r=10, t=30, b=10))

st.set_page_config(page_title="AuditIQ — Audit Intelligence", page_icon="🔍", layout="wide")

st.markdown(
    """
    <style>
      .aiq-card{background:#111827;border:1px solid rgba(255,255,255,0.08);
        border-radius:12px;padding:16px 18px;height:100%;}
      .aiq-card .lbl{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#64748b;}
      .aiq-card .val{font-size:1.7rem;font-weight:600;letter-spacing:-.02em;margin-top:4px;}
      .aiq-card .sub{font-size:12px;color:#94a3b8;margin-top:2px;}
      .aiq-badge{display:inline-block;padding:5px 14px;border-radius:20px;font-size:12px;
        font-weight:600;letter-spacing:.05em;color:#fff;}
      .aiq-finding{background:#111827;border-left:3px solid #64748b;border-radius:8px;
        padding:12px 16px;margin-bottom:10px;}
      .aiq-finding h4{margin:0 0 4px;font-size:14px;color:#f1f5f9;}
      .aiq-finding p{margin:0;font-size:13px;color:#94a3b8;line-height:1.5;}
      .aiq-summary{background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25);
        border-radius:12px;padding:16px 18px;margin:8px 0 4px;}
      .aiq-summary .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:#3b82f6;}
      .aiq-summary p{margin:6px 0 0;color:#e2e8f0;line-height:1.6;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _card(label: str, value: str, sub: str, color: str = "#f1f5f9") -> str:
    return (f'<div class="aiq-card" style="border-top:3px solid {color}">'
            f'<div class="lbl">{label}</div>'
            f'<div class="val" style="color:{color}">{value}</div>'
            f'<div class="sub">{sub}</div></div>')


def _guess_year(name: str) -> str:
    m = re.search(r"(20\d{2})", name)
    return m.group(1) if m else name.rsplit(".", 1)[0][:12]


def _beneish_color(b) -> str:
    if b is None:
        return GREY
    if b.is_manipulator:
        return RED
    return AMBER if b.m_score > b.threshold - 0.5 else GREEN


def run_analysis(files, industry: str) -> AuditReport:
    """Full pipeline for uploaded PDFs (requires API key)."""
    from auditiq.extraction.ai_extractor import extract_financials
    from auditiq.extraction.pdf_reader import read_pdf_bytes

    statements, benford_texts = [], {}
    with st.status("Running forensic analysis…", expanded=True) as status:
        for f in files:
            yr = _guess_year(f.name)
            st.write(f"📄 Reading **{f.name}**")
            content = read_pdf_bytes(f.getvalue())
            st.write(f"🤖 Extracting financials with Claude "
                     f"(scanned {content.scanned_pages} of {content.num_pages} pages)…")
            fs = extract_financials(content.financial_text, year_label=yr)
            statements.append(fs)
            benford_texts[fs.year or yr] = content.full_text

        st.write("📊 Scoring — Beneish · Altman · Benford · benchmarking…")
        company = next((s.company_name for s in statements if s.company_name), None)
        news = None
        if company:
            st.write("📰 Cross-referencing recent news sentiment…")
            news = get_news_sentiment(company)
        report = build_report(statements, industry=industry, benford_texts=benford_texts, news=news)
        if report.years:
            st.write("✍️ Writing the audit summary…")
            report.summary = generate_summary(report.years[-1], industry)
        status.update(label="✅ Analysis complete", state="complete")
    return report


def load_sample() -> AuditReport:
    report = build_report(get_sample_statements(), industry=SAMPLE_INDUSTRY)
    if report.years:  # attach a Benford demo population to the latest year
        report.years[-1].benford = benford_analyze(get_sample_benford_numbers())
    return report


# ─── Sidebar ──────────────────────────────────────────────────────────────────
def sidebar() -> str:
    with st.sidebar:
        st.markdown("### 🔍 AuditIQ")
        st.caption("Forensic audit intelligence")
        st.divider()

        ind_items = industries()
        keys = [k for k, _ in ind_items]
        labels = {k: lbl for k, lbl in ind_items}
        default = st.session_state.get("industry", "retail")
        industry = st.selectbox("Industry (for benchmarking)", keys,
                                index=keys.index(default) if default in keys else 0,
                                format_func=lambda k: labels[k])
        st.session_state["industry"] = industry

        st.divider()
        if settings.has_api_key:
            st.success("Claude API connected", icon="✅")
        else:
            st.warning("No ANTHROPIC_API_KEY — AI extraction & news disabled. "
                       "Use **Load sample data** to explore.", icon="⚠️")

        st.caption(f"Extraction model: `{settings.extraction_model}`")
        st.divider()
        if st.button("📊 Load sample data", use_container_width=True):
            st.session_state["report"] = load_sample()
            st.rerun()
        if st.session_state.get("report") and st.button("🗑️ Clear", use_container_width=True):
            st.session_state.pop("report", None)
            st.rerun()
    return industry


# ─── Result views ─────────────────────────────────────────────────────────────
def metric_cards(year: YearAnalysis) -> None:
    b, a, r = year.beneish, year.altman, year.ratios
    cols = st.columns(3)
    with cols[0]:
        c = _beneish_color(b)
        st.markdown(_card("Beneish M-Score", f"{b.m_score}" if b else "—",
                          ("⚠ Manipulator zone" if b and b.is_manipulator else "✓ Non-manipulator")
                          if b else "Needs 2 years", c), unsafe_allow_html=True)
    with cols[1]:
        c = _beneish_color(b)
        st.markdown(_card("Fraud probability", f"{b.probability}%" if b else "—",
                          "Probit-implied likelihood" if b else "Upload a prior year", c),
                    unsafe_allow_html=True)
    with cols[2]:
        c = RISK_COLOR[a.zone] if a else GREY
        st.markdown(_card("Altman Z-Score", f"{a.z_score}" if a else "—",
                          f"{a.zone_label} zone ({a.model_used})" if a else "Insufficient data", c),
                    unsafe_allow_html=True)

    cols = st.columns(3)
    gm = r.gross_margin
    gm_c = RED if gm is not None and gm < 0.2 else AMBER if gm is not None and gm < 0.35 else GREEN
    cr = r.current_ratio
    cr_c = RED if cr is not None and cr < 1 else AMBER if cr is not None and cr < 1.5 else GREEN
    rd = r.receivables_days
    rd_c = RED if rd is not None and rd > 90 else AMBER if rd is not None and rd > 60 else GREEN
    with cols[0]:
        st.markdown(_card("Gross margin", f"{gm*100:.1f}%" if gm is not None else "—",
                          "Profitability", gm_c), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(_card("Current ratio", f"{cr}x" if cr is not None else "—",
                          "Short-term liquidity", cr_c), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(_card("Receivables days", f"{rd:.0f}d" if rd is not None else "—",
                          "Cash collection speed", rd_c), unsafe_allow_html=True)


def overview_tab(report: AuditReport, year: YearAnalysis) -> None:
    if report.summary:
        st.markdown(f'<div class="aiq-summary"><div class="lbl">AI audit summary</div>'
                    f'<p>{report.summary}</p></div>', unsafe_allow_html=True)
    st.markdown("#### Findings")
    for f in year.findings:
        st.markdown(
            f'<div class="aiq-finding" style="border-left-color:{RISK_COLOR[f.level]}">'
            f'<h4>{f.icon} {f.title}'
            f'<span class="aiq-badge" style="background:{RISK_COLOR[f.level]};margin-left:8px;'
            f'font-size:10px;padding:2px 8px">{f.level.upper()}</span></h4>'
            f'<p>{f.body}</p></div>', unsafe_allow_html=True)


def beneish_tab(year: YearAnalysis) -> None:
    from auditiq.analysis.beneish import COMPONENT_INFO
    b = year.beneish
    if not b:
        st.info("The Beneish M-Score needs two consecutive years. Upload a prior year to compute it.")
        return
    st.caption("Eight ratios estimating earnings-manipulation probability. "
               f"Score **{b.m_score}** vs threshold **{b.threshold}** → "
               f"{'⚠ manipulator zone' if b.is_manipulator else '✓ non-manipulator zone'}.")
    keys = list(b.components)
    vals = [b.components[k] for k in keys]
    thresh = [COMPONENT_INFO.get(k, (k, '', 1))[2] for k in keys]
    bar_colors = [AMBER if v > t else GREEN for v, t in zip(vals, thresh)]
    fig = go.Figure(go.Bar(x=keys, y=vals, marker_color=bar_colors,
                           text=[f"{v:g}" for v in vals], textposition="outside"))
    fig.update_layout(height=320, title="M-Score components (amber = elevated)", **PLOTLY_BG)
    st.plotly_chart(fig, use_container_width=True)
    for k in keys:
        name, tip, t = COMPONENT_INFO.get(k, (k, "", 1))
        col = AMBER if b.components[k] > t else GREEN
        st.markdown(f"<span style='color:{col};font-family:monospace'>**{k}** {b.components[k]:g}</span> "
                    f"— {name}: {tip}", unsafe_allow_html=True)


def benford_tab(year: YearAnalysis) -> None:
    bf = year.benford
    if not bf or not bf.n:
        st.info("Benford's Law runs on the full numeric population of an uploaded PDF. "
                "Not available for this view.")
        return
    digits = [d.digit for d in bf.digits]
    fig = go.Figure()
    fig.add_bar(x=digits, y=[d.observed_pct for d in bf.digits], name="Observed", marker_color=ACCENT)
    fig.add_scatter(x=digits, y=[round(EXPECTED[d]*100, 2) for d in digits], name="Benford expected",
                    mode="lines+markers", line=dict(color=RED, dash="dash"))
    fig.update_layout(height=340, title=f"First-digit distribution (n={bf.n})",
                      xaxis_title="Leading digit", yaxis_title="% of values", **PLOTLY_BG)
    st.plotly_chart(fig, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Conformity", bf.conformity.title())
    c2.metric("MAD", f"{bf.mad}")
    c3.metric("Chi² (p)", f"{bf.chi_square} ({bf.p_value})")
    if bf.note:
        st.caption(bf.note)
    elif bf.suspicious:
        st.warning("Digit distribution deviates from Benford's Law — possible rounding or fabrication.")
    else:
        st.success("Digit distribution is broadly consistent with Benford's Law.")


def altman_tab(year: YearAnalysis) -> None:
    a = year.altman
    if not a:
        st.info("Altman Z-Score needs balance-sheet detail (assets, liabilities, equity).")
        return
    zones = ALTMAN_ZONES.get(a.model_used, ALTMAN_ZONES["original"])
    distress, safe = zones["distress"], zones["safe"]
    top = max(safe + 1, a.z_score + 1)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=a.z_score, title={"text": f"Altman Z ({a.model_used})"},
        gauge={"axis": {"range": [0, top]},
               "bar": {"color": RISK_COLOR[a.zone]},
               "steps": [{"range": [0, distress], "color": "rgba(239,68,68,0.25)"},
                         {"range": [distress, safe], "color": "rgba(245,158,11,0.25)"},
                         {"range": [safe, top], "color": "rgba(16,185,129,0.25)"}]}))
    fig.update_layout(height=300, **PLOTLY_BG)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Zone bands for the {a.model_used} model — "
               f"distress < {distress} · grey {distress}–{safe} · safe > {safe}")
    st.markdown(f"**Zone:** :{'red' if a.zone=='high' else 'orange' if a.zone=='medium' else 'green'}[{a.zone_label}]")
    st.write({k: v for k, v in a.components.items()})


def benchmark_tab(year: YearAnalysis) -> None:
    rows = year.benchmarks
    if not rows:
        st.info("No benchmark data.")
        return
    labels = [r.label for r in rows]
    fig = go.Figure()
    fig.add_bar(y=labels, x=[r.company or 0 for r in rows], name="Company",
                orientation="h", marker_color=ACCENT)
    fig.add_bar(y=labels, x=[r.industry for r in rows], name="Industry",
                orientation="h", marker_color=GREY)
    fig.update_layout(height=360, barmode="group", title="Company vs industry", **PLOTLY_BG)
    st.plotly_chart(fig, use_container_width=True)
    import pandas as pd
    df = pd.DataFrame([{
        "Metric": r.label,
        "Company": "N/A" if r.company is None else f"{r.company}{r.unit}",
        "Industry": f"{r.industry}{r.unit}",
        "Status": r.flag.upper(),
    } for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True)


def trends_tab(report: AuditReport) -> None:
    comp = report.comparison
    if not comp or len(comp.points) < 2:
        st.info("Upload 2–3 years to unlock trend analysis.")
        return
    yrs = [p.year for p in comp.points]
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_bar(x=yrs, y=[p.revenue for p in comp.points], name="Revenue", marker_color=ACCENT)
        fig.add_bar(x=yrs, y=[p.net_income for p in comp.points], name="Net income", marker_color=GREEN)
        fig.update_layout(height=300, barmode="group", title="Revenue & net income", **PLOTLY_BG)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = go.Figure()
        fig.add_scatter(x=yrs, y=[p.m_score for p in comp.points], name="M-Score",
                        mode="lines+markers", line=dict(color=AMBER))
        fig.add_scatter(x=yrs, y=[-1.78]*len(yrs), name="Threshold",
                        mode="lines", line=dict(color=RED, dash="dash"))
        fig.update_layout(height=300, title="Beneish M-Score over time", **PLOTLY_BG)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"**Direction of travel:** :{'red' if comp.direction=='worsening' else 'green' if comp.direction=='improving' else 'gray'}[{comp.direction.title()}]")
    for n in comp.notes:
        st.markdown(f"- {n}")


def news_tab(report: AuditReport) -> None:
    n = report.news
    if not n:
        st.info("News sentiment requires the Claude API with web search. "
                "It runs automatically on uploaded reports when a company name is detected.")
        return
    color = RISK_COLOR["high"] if n.score < -0.15 else RISK_COLOR["low"] if n.score > 0.15 else AMBER
    st.markdown(_card("News sentiment", f"{n.label} ({n.score:+.2f})", f"as of {n.as_of}", color),
                unsafe_allow_html=True)
    st.write(n.summary)
    if n.flags:
        st.markdown("**Signals:** " + "; ".join(n.flags))
    for art in n.articles:
        src = f" · {art.source}" if art.source else ""
        link = f"[{art.title}]({art.url})" if art.url else art.title
        st.markdown(f"- {link}{src} ({art.date or 'n/a'})")


def report_tab(report: AuditReport) -> None:
    st.write("Generate a professional, shareable PDF of the full analysis.")
    if st.button("📄 Generate PDF report", type="primary"):
        from auditiq.reporting.pdf_report import report_bytes
        with st.spinner("Building report…"):
            data = report_bytes(report)
        st.download_button("⬇️ Download report", data=data,
                           file_name=f"AuditIQ_{report.company_name.replace(' ', '_')}.pdf",
                           mime="application/pdf")
        st.success("Report ready.")


# ─── Upload landing ───────────────────────────────────────────────────────────
def upload_view(industry: str) -> None:
    st.markdown("## Upload annual report")
    st.caption("PDF — up to 3 years for trend analysis & the Beneish M-Score")
    files = st.file_uploader("Drop annual report PDFs", type="pdf", accept_multiple_files=True)
    disabled = not settings.has_api_key
    if st.button("🚀 Run analysis", type="primary", disabled=disabled):
        if not files:
            st.error("Please upload at least one PDF.")
        elif len(files) > 3:
            st.error("Please upload at most 3 reports.")
        else:
            try:
                st.session_state["report"] = run_analysis(files, industry)
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Analysis failed: {exc}")
    if disabled:
        st.info("Set `ANTHROPIC_API_KEY` in `.env` to enable PDF analysis, or click "
                "**Load sample data** in the sidebar to explore the dashboard now.")
    cols = st.columns(2)
    bullets = ["Revenue & gross-margin trends", "Receivables & inventory days",
               "Cash flow vs net income (accruals)", "Beneish M-Score (8 factors)",
               "Altman Z-Score (bankruptcy)", "Benford's Law (digit anomalies)",
               "Industry benchmarking", "AI-written audit summary"]
    for i, bl in enumerate(bullets):
        cols[i % 2].markdown(f"✓ {bl}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def results_view(report: AuditReport) -> None:
    risk = report.overall_risk
    left, right = st.columns([3, 1])
    with left:
        st.markdown(f"## {report.company_name}")
        st.caption(f"{report.industry.title()} · years: {', '.join(y.year for y in report.years)}")
    with right:
        st.markdown(f'<div style="text-align:right"><span class="aiq-badge" '
                    f'style="background:{RISK_COLOR[risk]}">{RISK_TEXT[risk]}</span></div>',
                    unsafe_allow_html=True)

    yrs = [y.year for y in report.years]
    sel = st.radio("Year", yrs, index=len(yrs)-1, horizontal=True) if len(yrs) > 1 else yrs[0]
    year = next(y for y in report.years if y.year == sel)

    metric_cards(year)
    st.write("")
    tabs = st.tabs(["Overview", "Beneish", "Benford", "Altman", "Benchmarking", "Trends", "News", "Report"])
    with tabs[0]:
        overview_tab(report, year)
    with tabs[1]:
        beneish_tab(year)
    with tabs[2]:
        benford_tab(year)
    with tabs[3]:
        altman_tab(year)
    with tabs[4]:
        benchmark_tab(year)
    with tabs[5]:
        trends_tab(report)
    with tabs[6]:
        news_tab(report)
    with tabs[7]:
        report_tab(report)


def main() -> None:
    industry = sidebar()
    report = st.session_state.get("report")
    if report is None:
        st.markdown("# 🔍 AuditIQ")
        st.markdown("#### Audit intelligence. *In seconds.*")
        upload_view(industry)
    else:
        results_view(report)


if __name__ == "__main__":
    main()

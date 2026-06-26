# AuditIQ — AI-Powered Forensic Audit Intelligence

Upload a company's annual report (PDF) and get a full forensic risk assessment in
seconds: earnings-manipulation scoring, bankruptcy risk, numeric-manipulation
detection, industry benchmarking, multi-year trend analysis, news cross-referencing,
and an exportable professional report — powered by the same models real auditors use,
with narrative analysis from Claude.

> ⚠️ **Not a substitute for qualified audit advice.** AuditIQ is an analytical
> screening tool. All scores are model estimates and must be reviewed by a professional.

## Features

| # | Capability | Module |
|---|------------|--------|
| 1 | Upload annual report PDFs | `auditiq/extraction/pdf_reader.py` |
| 2 | Extract & analyse financials for red flags | `auditiq/extraction/ai_extractor.py`, `auditiq/analysis/findings.py` |
| 3 | Beneish M-Score (fraud probability) | `auditiq/analysis/beneish.py` |
| 4 | Benford's Law (manipulated-number detection) | `auditiq/analysis/benford.py` |
| 5 | Altman Z-Score (bankruptcy risk) | `auditiq/analysis/altman.py` |
| 6 | Industry-average benchmarking | `auditiq/analysis/benchmark.py` |
| 7 | Up-to-3-year comparison | `auditiq/analysis/comparison.py` |
| 8 | News sentiment cross-reference | `auditiq/intelligence/news.py` |
| 9 | Professional PDF report | `auditiq/reporting/pdf_report.py` |
| 10 | Interactive dashboard | `app.py` (Streamlit) |

## Architecture

```
auditiq/
├── config.py              # settings, paths, model + threshold constants
├── models.py              # pydantic data models (financials, results, findings)
├── extraction/
│   ├── pdf_reader.py      # pdfplumber text + table extraction
│   └── ai_extractor.py    # Claude structured financial extraction
├── analysis/
│   ├── beneish.py         # Beneish M-Score (earnings manipulation)
│   ├── benford.py         # Benford's Law (digit-distribution anomalies)
│   ├── altman.py          # Altman Z-Score (bankruptcy risk)
│   ├── ratios.py          # financial ratios
│   ├── benchmark.py       # industry benchmarking
│   ├── findings.py        # rules-based red-flag synthesis
│   └── comparison.py      # multi-year trend analysis
├── intelligence/
│   ├── llm.py             # Anthropic client wrapper
│   └── news.py            # Claude + web-search news sentiment
├── reporting/
│   └── pdf_report.py      # reportlab professional report
└── data/
    └── industry_benchmarks.json

app.py                     # Streamlit dashboard (entry point)
prototype/                 # original HTML/JS design mockup (reference)
tests/                     # pytest unit tests for the analysis engines
```

The **deterministic engines** (Beneish, Benford, Altman, ratios, benchmarking)
run with no API key. **AI features** (PDF extraction, narrative findings, news)
require `ANTHROPIC_API_KEY`.

## Setup

Requires **Python 3.12** (native, not the system 3.7).

```bash
# 1. Create the virtualenv (already done by the scaffolder as .venv)
python3.12 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY

# 4. Run the dashboard
streamlit run app.py
```

The dashboard includes a **"Load sample data"** mode so you can explore the full
analysis flow without an API key or a PDF.

## Tests

```bash
.venv/bin/pytest -q
```

## Deploy

See **[DEPLOY.md](DEPLOY.md)** — Streamlit Community Cloud, Docker (`docker compose up --build`),
or Cloud Run / Fly / Render. Full design docs live in **[docs/](docs/README.md)**.

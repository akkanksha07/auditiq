# AuditIQ — Code Map

> **Status:** Draft v0.1 · **Date:** 2026-06-25 · **Audience:** engineers, reviewers, new contributors
>
> A file-by-file reference to the AuditIQ codebase: what each file is *supposed to do*, its
> public API, key behaviours, and how it connects to the rest of the system. For the higher-level
> picture see [TECH_ARCHITECTURE.md](TECH_ARCHITECTURE.md); for exact behaviour/formulas see
> [FUNCTIONAL_SPEC.md](FUNCTIONAL_SPEC.md).

## How to read this document
Files are grouped by architectural layer, in dependency order (leaf modules first, UI last):

1. [Project & config files](#1-project--config-files)
2. [Core package](#2-core-package-auditiq) — `config`, `models`, `pipeline`, `sample_data`
3. [Extraction layer](#3-extraction-layer-auditiqextraction)
4. [Analysis engines](#4-analysis-engines-auditiqanalysis)
5. [Intelligence / AI layer](#5-intelligence--ai-layer-auditiqintelligence)
6. [Reporting layer](#6-reporting-layer-auditiqreporting)
7. [Data assets](#7-data-assets)
8. [Entry point — dashboard](#8-entry-point--dashboard)
9. [Tests](#9-tests)
10. [Prototype (design reference)](#10-prototype-design-reference)

**Layering rule:** the **deterministic core** (`analysis/*`, `ratios`, `benchmark`, `pipeline`,
`models`, `config`) has *no* network/LLM dependency and runs offline. The **AI layer**
(`extraction/ai_extractor`, `intelligence/*`) wraps the Anthropic API and degrades gracefully
without an `ANTHROPIC_API_KEY`. The **UI** (`app.py`) and **reporting** (`pdf_report`) sit on top.

---

## Annotated directory tree

```
auditai/
├── app.py                      # Streamlit dashboard — application entry point
├── requirements.txt            # Pinned dependency ranges (Python 3.12)
├── pytest.ini                  # pytest config (pythonpath=., testpaths=tests)
├── .env.example                # Template for secrets/model overrides
├── .gitignore                  # Ignore venv, caches, secrets, uploaded data
├── README.md                   # Project overview + setup/run instructions
├── .streamlit/
│   └── config.toml             # Streamlit dark theme (AuditIQ palette) + server opts
├── auditiq/                    # ── Python package (all application logic) ──
│   ├── __init__.py             # Version + brand constants
│   ├── config.py               # Settings (env), paths, analysis constants/thresholds
│   ├── models.py               # Pydantic v2 data models (the domain vocabulary)
│   ├── pipeline.py             # Orchestration: statements → YearAnalysis → AuditReport
│   ├── sample_data.py          # Offline demo dataset (no API key needed)
│   ├── data/
│   │   └── industry_benchmarks.json   # 6 sectors × 8 benchmark metrics
│   ├── extraction/
│   │   ├── pdf_reader.py       # pdfplumber text/table extraction
│   │   └── ai_extractor.py     # Claude → structured FinancialStatement
│   ├── analysis/               # ── Deterministic forensic engines ──
│   │   ├── beneish.py          # Beneish M-Score (earnings manipulation)
│   │   ├── benford.py          # Benford's Law (digit-distribution anomalies)
│   │   ├── altman.py           # Altman Z-Score (bankruptcy risk)
│   │   ├── ratios.py           # Financial ratio computations
│   │   ├── benchmark.py        # Ratios vs industry averages + flags
│   │   ├── findings.py         # Rules-based red-flag synthesis
│   │   └── comparison.py       # Multi-year trend & direction-of-travel
│   ├── intelligence/           # ── AI layer (needs ANTHROPIC_API_KEY) ──
│   │   ├── llm.py              # Anthropic client wrapper + JSON helpers
│   │   ├── news.py            # News sentiment via Claude + web search
│   │   └── summary.py          # Narrative audit summary (senior-auditor voice)
│   └── reporting/
│       └── pdf_report.py       # Professional PDF report (reportlab + matplotlib)
├── data/                       # Runtime data (gitignored contents)
│   ├── uploads/                # Uploaded PDFs
│   └── reports/                # Generated PDF reports
├── tests/                      # pytest unit/integration tests (15 tests)
│   ├── test_beneish.py
│   ├── test_benford.py
│   ├── test_altman.py
│   ├── test_ratios_benchmark.py
│   └── test_pipeline.py
└── prototype/                  # Original HTML/JS/CSS mockup — design source of truth
    ├── index.html  ├── app.html  ├── app.js  └── style.css
```

## Summary table

| File | Layer | One-line responsibility |
|---|---|---|
| `app.py` | UI | Streamlit dashboard, upload + results tabs, demo mode |
| `auditiq/config.py` | Core | Env settings, paths, thresholds (Beneish/Altman/Benford) |
| `auditiq/models.py` | Core | Pydantic models for financials & all results |
| `auditiq/pipeline.py` | Core | Orchestrate engines into a full `AuditReport` |
| `auditiq/sample_data.py` | Core | Offline demo data + Benford population |
| `auditiq/extraction/pdf_reader.py` | Extraction | Extract text/tables from PDFs (pdfplumber) |
| `auditiq/extraction/ai_extractor.py` | Extraction (AI) | Claude → `FinancialStatement` JSON |
| `auditiq/analysis/beneish.py` | Engine | 8-factor Beneish M-Score + probability |
| `auditiq/analysis/benford.py` | Engine | First-digit Benford analysis (χ², MAD) |
| `auditiq/analysis/altman.py` | Engine | Altman Z / Z' / Z'' bankruptcy score |
| `auditiq/analysis/ratios.py` | Engine | Financial ratios from a statement |
| `auditiq/analysis/benchmark.py` | Engine | Ratio vs sector benchmarking + flags |
| `auditiq/analysis/findings.py` | Engine | Aggregate engines → ranked `Finding`s |
| `auditiq/analysis/comparison.py` | Engine | Multi-year trend & direction |
| `auditiq/intelligence/llm.py` | AI | Anthropic client wrapper + `extract_json` |
| `auditiq/intelligence/news.py` | AI | News sentiment via Claude web search |
| `auditiq/intelligence/summary.py` | AI | Plain-English audit summary |
| `auditiq/reporting/pdf_report.py` | Reporting | Build the downloadable PDF report |
| `auditiq/data/industry_benchmarks.json` | Data | Sector benchmark constants |
| `tests/*` | Tests | Verify the deterministic core (15 tests) |

---

## 1. Project & config files

### `requirements.txt`
**Purpose:** declare the Python dependency set with compatible version ranges, pinned for Python 3.12.
**Contents:** Streamlit (UI); pandas/numpy/scipy (numerics; scipy powers Benford χ² and the Beneish probit CDF); pdfplumber (PDF parsing); anthropic + python-dotenv (AI + env); pydantic v2 (models); plotly (dashboard charts) + matplotlib (PDF charts); reportlab (PDF); pytest (tests).
**Notes:** install into the project venv only — the machine's system `python3` is a broken x86_64 Python 3.7. Use `.venv/bin/pip install -r requirements.txt`.

### `pytest.ini`
**Purpose:** make the test suite runnable from the repo root. Sets `pythonpath = .` (so `import auditiq` resolves), `testpaths = tests`, and `addopts = -q`.

### `.env.example`
**Purpose:** template documenting every environment variable. Copy to `.env`. Defines `ANTHROPIC_API_KEY` (required for AI features) and optional model overrides (`AUDITIQ_EXTRACTION_MODEL`, `AUDITIQ_NARRATIVE_MODEL`, `AUDITIQ_NEWS_MODEL`) and `AUDITIQ_MAX_PDF_PAGES`.

### `.gitignore`
**Purpose:** keep the repo clean — ignores `.venv/`, `__pycache__/`, caches, `.env`, and the *contents* of `data/uploads` and `data/reports` (keeping the folders via `.gitkeep`).

### `.streamlit/config.toml`
**Purpose:** Streamlit theming + server config. Encodes the AuditIQ dark palette (`base="dark"`, `backgroundColor=#0a0f1e`, `primaryColor=#3b82f6`, etc.), 50 MB upload cap, headless mode, and disables usage stats. This is what makes the dashboard match the prototype's look without per-widget styling.

### `README.md`
**Purpose:** human entry point — what AuditIQ is, the 10-feature table mapped to modules, the architecture tree, setup/run steps, and the disclaimer.

---

## 2. Core package (`auditiq/`)

### `auditiq/__init__.py`
**Purpose:** marks the package and exposes `__version__ = "0.1.0"` and `__brand__ = "AuditIQ"`. No logic.

### `auditiq/config.py`
**Purpose:** single source of truth for runtime configuration, filesystem paths, and analysis constants. Imported by almost everything.
**Responsibilities:**
- Load `.env` via `python-dotenv` at import.
- Resolve and **create** the data directories (`DATA_DIR`, `UPLOAD_DIR`, `REPORT_DIR`) and locate `BENCHMARKS_PATH`.
- Provide a frozen `Settings` dataclass read from the environment.
- Define the numeric constants every engine references, so thresholds live in one place.

**Public API / key symbols:**
- `Settings` (frozen dataclass): `anthropic_api_key`, `extraction_model`, `narrative_model`, `news_model`, `max_pdf_pages`; property `has_api_key`.
- `settings` — the singleton instance used app-wide.
- Paths: `PKG_DIR`, `BASE_DIR`, `DATA_DIR`, `UPLOAD_DIR`, `REPORT_DIR`, `BENCHMARKS_PATH`.
- Constants: `BENEISH_THRESHOLD = -1.78`, `BENEISH_THRESHOLD_5VAR = -2.22`, `ALTMAN_ZONES` (per-variant safe/distress cutoffs), `BENFORD_MAD_THRESHOLDS` (Nigrini bands), `BENFORD_MIN_SAMPLE = 50`, `RISK_LEVELS`.

**Used by:** every analysis engine (thresholds), `llm.py` (key/models), `pdf_reader.py` (page cap), `pdf_report.py` (report dir), `benchmark.py` (benchmarks path).

### `auditiq/models.py`
**Purpose:** the domain vocabulary — typed pydantic v2 models passed between every layer. Guarantees structure and validates LLM output.
**Responsibilities:**
- Define the extraction target and every analysis result as a model.
- Accept the **camelCase** JSON aliases emitted by the Claude extraction prompt while exposing **snake_case** Python attributes (`populate_by_name=True`, `extra="ignore"`).
- Provide derived helpers so engines don't recompute common quantities.

**Key models:**
- `FinancialStatement` — one year of financials (all monetary fields `Optional[float]`, in millions). Income-statement, cash-flow, and balance-sheet fields plus qualitative `red_flags` / `notes`. Derived properties: `working_capital`, `resolved_total_liabilities` (falls back to assets − equity, then total_debt), `resolved_gross_profit` (falls back to revenue − COGS).
- `BeneishResult` — `m_score`, `probability`, `is_manipulator`, `threshold`, `components` (the 8 indices).
- `BenfordDigit` / `BenfordResult` — per-digit observed/expected/deviation; plus `n`, `chi_square`, `p_value`, `mad`, `conformity`, `suspicious`, `note`.
- `AltmanResult` — `model_used`, `z_score`, `zone` (low/medium/high), `zone_label`, `components` (X1–X5).
- `RatioSet` — the eight computed ratios.
- `BenchmarkRow` — one metric vs industry with `flag` (ok/medium/high) and `higher_is_bad`.
- `Finding` — `level`, `category`, `title`, `body`, `icon` (the unit of the findings feed).
- `NewsArticle` / `NewsSentiment` — article list + overall score/label/flags (`NewsArticle` ignores extra keys for robustness against the LLM).
- `YearAnalysis` — bundles one year's `financials`, `ratios`, `benchmarks`, `beneish`, `altman`, `benford`, `findings`.
- `TrendPoint` / `Comparison` — multi-year series + `direction` + `notes`.
- `AuditReport` — top-level object: company, industry, `years`, `comparison`, `news`, `summary`, `overall_risk`, `generated_at`.
**Type aliases:** `RiskLevel = Literal["low","medium","high"]`, `Flag = Literal["ok","medium","high"]`.
**Used by:** every module — this is the lingua franca.

### `auditiq/pipeline.py`
**Purpose:** orchestration glue. Turns extracted statements into per-year analyses and a complete `AuditReport`. **Deliberately free of network/LLM calls** so it is fully unit-testable offline; AI-derived inputs (news, summary) are injected by the caller.
**Public API:**
- `analyze_year(financials, *, industry, prior=None, benford_text=None) -> YearAnalysis` — runs ratios → benchmark → Beneish (needs `prior`) → Altman → Benford (if text given) → findings for a single year.
- `build_report(statements, *, industry, benford_texts=None, news=None, summary="") -> AuditReport` — sorts statements chronologically, walks them carrying the previous year as `prior` (for Beneish), builds the comparison, computes worst-case `overall_risk`, and assembles the report.
**Depends on:** all `analysis/*` engines + `models`. **Used by:** `app.py` and `tests/test_pipeline.py`.

### `auditiq/sample_data.py`
**Purpose:** ship a realistic, deterministic dataset so the dashboard and tests work with **no API key and no PDF**.
**Public API:**
- `SAMPLE_INDUSTRY = "retail"`.
- `get_sample_statements() -> list[FinancialStatement]` — "Northgate Retail Group", 3 years (2021–2023). Numbers are tuned so the latest year shows accelerating receivables, margin compression, high accruals and rising leverage → an **elevated Beneish M-Score** with mixed benchmark flags (a deliberately interesting forensic case).
- `get_sample_benford_numbers() -> list[float]` — 400 values, `round(10**((k+0.5)/400) * 10**(k%6), 2)`: the `10**((k+0.5)/400)` mantissa makes first digits follow Benford by construction, while the `10**(k%6)` factor spreads magnitudes so the values look like money (demonstrates the *clean* Benford case).
**Used by:** `app.py` (Load sample data) and several tests.

---

## 3. Extraction layer (`auditiq/extraction/`)

### `auditiq/extraction/pdf_reader.py`
**Purpose:** deterministic PDF parsing — turn a PDF (path or bytes) into text and tables. No AI here.
**Public API:**
- `PdfContent` (dataclass): `full_text`, `page_texts`, `tables`, `num_pages`; property `financial_text` returns only pages whose text matches statement keywords ("balance sheet", "income statement", "cash flow", …), falling back to the whole document. This focuses the AI extractor and reduces token cost.
- `read_pdf(path, max_pages=None) -> PdfContent` and `read_pdf_bytes(data, max_pages=None) -> PdfContent` (the Streamlit uploader hands over bytes). Page count capped by `settings.max_pdf_pages`.
**Depends on:** `pdfplumber`, `config.settings`. **Used by:** `app.py`; its `full_text` feeds Benford, `financial_text` feeds the AI extractor.

### `auditiq/extraction/ai_extractor.py`
**Purpose:** the AI extraction step — ask Claude to read messy report text and return a strict JSON financial statement.
**Public API:**
- `extract_financials(text, year_label, model=None) -> FinancialStatement` — builds the schema-constrained prompt, calls `llm.complete`, parses with `llm.extract_json`, defaults the year, and validates into a `FinancialStatement`.
- `_prompt(text, year_label)` — the prompt: forensic-analyst persona, exact JSON schema (all the camelCase fields), guidance on EBIT/total debt/market value/red flags, truncates input to 15k chars.
**Depends on:** `intelligence.llm`, `config`, `models`. **Requires:** `ANTHROPIC_API_KEY`.

---

## 4. Analysis engines (`auditiq/analysis/`)

### `auditiq/analysis/beneish.py`
**Purpose:** compute the 8-factor **Beneish M-Score** (earnings-manipulation probability). Needs two consecutive years.
**Public API:**
- `compute_beneish(current, prior, threshold=BENEISH_THRESHOLD) -> Optional[BeneishResult]` — returns `None` if no prior. Computes DSRI, GMI, AQI, SGI, DEPI, SGAI, TATA, LVGI; the M-score; `is_manipulator = M > -1.78`; and `probability = Φ(M)*100` (the model's true **probit** probability via `scipy.stats.norm.cdf` — a deliberate correctness improvement over the prototype's ad-hoc logistic).
- `COMPONENT_INFO` — per-indicator `(name, plain-English tip, "elevated" threshold)` used by the UI and report.
- `elevated_components(result) -> list[str]` — indicators above their elevated threshold (drives the "key drivers" finding).
- Helpers: `_safe_div` (index-safe division, default 1.0), `_noncurrent_soft_assets`, `_accruals`.
**Behavioural notes:** TATA defaults to `0.0` (neutral) when assets are missing; LVGI uses total liabilities (via `resolved_total_liabilities`), not just debt.
**Depends on:** `scipy`, `config`, `models`. **Tested by:** `test_beneish.py`.

### `auditiq/analysis/benford.py`
**Purpose:** **Benford's Law** first-digit analysis to flag fabricated/rounded numbers.
**Public API:**
- `EXPECTED` — `{d: log10(1 + 1/d)}` for digits 1–9.
- `first_digit(value) -> Optional[int]` — leading significant digit of `|value|`.
- `extract_numbers(text) -> list[float]` — regex pulls number-like tokens (commas, currency symbols, parenthetical negatives), keeps `|x| >= 1`.
- `analyze(numbers) -> BenfordResult` — builds the distribution, computes χ² (df=8) via `scipy.stats.chisquare`, MAD, Nigrini conformity band (`close/acceptable/marginal/nonconformity`), and `suspicious` (nonconforming or p<0.05). Samples below `BENFORD_MIN_SAMPLE` (50) get a `note` and are never marked suspicious.
- `analyze_text(text)` — convenience: `analyze(extract_numbers(text))`.
**Known i18n limitation:** `extract_numbers` assumes Anglo formatting (`1,234.56`) — European/Indian grouping is a documented gap (see [TEST_PLAN.md](TEST_PLAN.md)).
**Tested by:** `test_benford.py`.

### `auditiq/analysis/altman.py`
**Purpose:** **Altman Z-Score** bankruptcy risk with three published variants.
**Public API:**
- `compute_altman(s, model="auto") -> Optional[AltmanResult]` — returns `None` without assets/liabilities. `_select_model` picks `original` (public manufacturer with market value), `private` (book equity), or `emerging`/Z'' (non-manufacturing; in `NON_MANUFACTURING`). Computes X1–X5 (X5 dropped for Z''), the score, and the zone (low=Safe / medium=Grey / high=Distress) from `ALTMAN_ZONES`.
- `NON_MANUFACTURING` — sectors routed to Z''.
**Tested by:** `test_altman.py`.

### `auditiq/analysis/ratios.py`
**Purpose:** compute the financial ratios used in cards, benchmarking, and findings.
**Public API:** `compute_ratios(s, prior=None) -> RatioSet` — receivables/inventory days, gross margin, current ratio, debt/equity, interest coverage, asset turnover, revenue growth (needs `prior`). COGS falls back to ≈70% of revenue when missing; debt/equity prefers `total_debt` then total liabilities. Division-by-zero/None returns `None`.
**Tested by:** `test_ratios_benchmark.py`.

### `auditiq/analysis/benchmark.py`
**Purpose:** compare a `RatioSet` against sector averages and flag deviations.
**Public API:**
- `load_benchmarks()` (cached) — reads `industry_benchmarks.json`.
- `industries() -> list[(key,label)]` — for selectors.
- `benchmark_ratios(ratios, industry) -> list[BenchmarkRow]` — one row per metric with severity `flag`. Flag rules encode auditor heuristics (e.g. receivables >1.3×→high/>1.1×→medium; current ratio <1.0→high; interest coverage <2.0→high; gross margin <0.8×→high).
- `_flag_high(...)` — shared higher-is-worse helper.
**Tested by:** `test_ratios_benchmark.py`.

### `auditiq/analysis/findings.py`
**Purpose:** synthesise all engine outputs into a ranked, human-readable findings feed.
**Public API:**
- `build_findings(financials, beneish, altman, benford, benchmarks) -> list[Finding]` — emits findings for manipulator-zone Beneish (with key drivers), Altman distress/grey, Benford anomaly, high then medium benchmark deviations, and up to four textual red flags; if nothing fires, a single "all clear" finding.
- `overall_risk(findings) -> RiskLevel` — worst level present.
**Used by:** `pipeline.analyze_year`.

### `auditiq/analysis/comparison.py`
**Purpose:** multi-year trend analysis (the "are they getting riskier?" view).
**Public API:** `build_comparison(years) -> Optional[Comparison]` — `None` for <2 years; otherwise builds `TrendPoint`s (revenue, net income, M-score, Z-score, gross margin) and a `direction` (improving/stable/worsening) from a tolerance-based heuristic (rising M-score / falling Z / margin compression / falling income = worse). Helper `_trend(first, last, tol)`.
**Tested by:** `test_pipeline.py` (indirectly).

---

## 5. Intelligence / AI layer (`auditiq/intelligence/`)

### `auditiq/intelligence/llm.py`
**Purpose:** the only place that talks to the Anthropic SDK; everything AI goes through here.
**Public API:**
- `get_client()` (cached) — constructs `anthropic.Anthropic`; raises `LLMError` if no key.
- `complete(prompt, *, model=None, max_tokens=1500, system=None, tools=None, temperature=0.0) -> str` — single-turn call; assembles text blocks (also used for server-tool calls like web search, where it returns the model's final text).
- `extract_json(text)` — robust JSON parse tolerant of code fences / surrounding prose.
- `LLMError` — raised when the LLM is unavailable/misconfigured.
**Used by:** `ai_extractor`, `news`, `summary`.

### `auditiq/intelligence/news.py`
**Purpose:** news-sentiment cross-reference via **Claude + the web-search server tool**.
**Public API:**
- `WEB_SEARCH_TOOL` — the `web_search_20250305` tool spec.
- `get_news_sentiment(company_name, model=None) -> Optional[NewsSentiment]` — returns `None` if no company / no key / any failure (fully graceful). Prompts Claude to search recent news for financial/governance/fraud signals and return structured JSON (score, label, summary, flags, articles); parses into `NewsSentiment`.
**Notes:** requires web search enabled on the Anthropic account.

### `auditiq/intelligence/summary.py`
**Purpose:** generate the plain-English "senior auditor" narrative shown at the top of the dashboard/report.
**Public API:** `generate_summary(year, industry, model=None) -> str` — returns `""` without a key or on failure. Feeds Claude the year's Beneish/Altman/benchmark deviations/red flags and asks for a 3–4 sentence, most-important-risk-first summary.

---

## 6. Reporting layer (`auditiq/reporting/`)

### `auditiq/reporting/pdf_report.py`
**Purpose:** render a complete `AuditReport` into a professional, shareable PDF.
**Public API:**
- `report_bytes(report) -> bytes` — build the PDF in memory (used by the dashboard's download button).
- `generate_report(report, out_path=None) -> Path` — write to disk (defaults to `data/reports/AuditIQ_<company>_<timestamp>.pdf`).
**Internals:** brand colour constants; matplotlib chart helpers (`_benford_fig`, `_trend_fig`) embedded via `_fig_image`; section builders (`_cover` with risk badge, `_summary`, `_metrics`, `_findings`, `_beneish_table`, `_benchmark_table`, `_news`, `_methodology`) assembled by `_build_story`. Uses the headless `Agg` matplotlib backend and reportlab Platypus.
**Depends on:** `reportlab`, `matplotlib`, `config`, `models`, `analysis.beneish` (component labels).

---

## 7. Data assets

### `auditiq/data/industry_benchmarks.json`
**Purpose:** the benchmark constants behind feature #6. Six sectors (`retail`, `technology`, `manufacturing`, `financial`, `healthcare`, `energy`), each with eight metrics (`receivablesDays`, `inventoryDays`, `grossMargin`, `currentRatio`, `debtToEquity`, `interestCoverage`, `assetTurnover`, `revenueGrowth`) and a display `label`. Ported verbatim from the prototype so numbers stay consistent. Edit here to retune benchmarks.

---

## 8. Entry point — dashboard

### `app.py`
**Purpose:** the Streamlit application — the interactive dashboard (feature #10) that ties every module together.
**Structure / key functions:**
- Page config + injected CSS (AuditIQ card / badge / finding / summary styles); plotly dark layout constants.
- `sidebar() -> str` — industry selector, API-key status, **Load sample data** / **Clear** buttons; persists choice in `session_state`.
- `upload_view(industry)` — landing screen: multi-file PDF uploader (≤3), **Run analysis** button (disabled without a key), and the "what we analyse" grid.
- `run_analysis(files, industry) -> AuditReport` — the live pipeline with `st.status` progress: read PDF bytes → `extract_financials` (Claude) → collect Benford text → `build_report` → `get_news_sentiment` → `generate_summary`.
- `load_sample() -> AuditReport` — offline path via `build_report(get_sample_statements())`, attaching a Benford demo population.
- `results_view(report)` — header + risk badge, year selector, `metric_cards`, and the eight tabs.
- Tab renderers: `overview_tab` (summary + findings feed), `beneish_tab` (component bar + explanations), `benford_tab` (observed-vs-expected chart + stats), `altman_tab` (gauge + components), `benchmark_tab` (grouped bar + table), `trends_tab` (revenue/income + M-score over time), `news_tab`, `report_tab` (generate + download PDF).
- Helpers: `_card` (HTML metric card), `_guess_year` (year from filename), `_beneish_color` (status colour), `metric_cards`.
- `main()` — routes between `upload_view` and `results_view` based on `session_state["report"]`.
**Run:** `.venv/bin/streamlit run app.py`. **Depends on:** `pipeline`, `models`, `sample_data`, `benchmark`, `benford`, `intelligence.*`, and (lazily) `extraction.*`, `reporting.pdf_report`.

---

## 9. Tests

All tests target the **deterministic core** (no API key needed) and run via `.venv/bin/pytest` (15 tests, all passing). AI paths are not unit-tested here because they require a live key (candidate for mocking — see [TEST_PLAN.md](TEST_PLAN.md)).

| File | Covers |
|---|---|
| `tests/test_beneish.py` | `compute_beneish`: None without prior; known −2.48 for identical clean years; sample latest year breaches −1.78. |
| `tests/test_benford.py` | `EXPECTED` sums to 1; `first_digit`; `extract_numbers` formats; conforming vs non-conforming + small-sample handling. |
| `tests/test_altman.py` | Model auto-selection; healthy=Safe; distressed=Distress; missing data → None. |
| `tests/test_ratios_benchmark.py` | Ratio values on sample; benchmark flag logic; benchmark-data integrity. |
| `tests/test_pipeline.py` | Offline `build_report`: per-year Beneish/Altman, comparison, overall risk, findings. |

---

## 10. Prototype (design reference)

### `prototype/index.html`, `app.html`, `app.js`, `style.css`
**Purpose:** the original **client-side mockup** of AuditIQ (landing page + tabbed tool, simulated logic, pdf.js + Chart.js). It is the **design source of truth**: branding ("AuditIQ", `AI` logo mark), the dark-navy palette and fonts (Inter + IBM Plex Mono), the tab layout, and the original industry-benchmark numbers and Beneish/ratio conventions the Python app reproduces. **Not executed by the Python app** — consult it before changing UI, branding, or benchmark values. The Python implementation extends it with real Benford, Altman, news, and PDF reporting.

---

*Cross-references:* [README](README.md) · [PRD](PRD.md) · [Technical Architecture](TECH_ARCHITECTURE.md) · [Functional Spec](FUNCTIONAL_SPEC.md) · [Test Plan](TEST_PLAN.md)

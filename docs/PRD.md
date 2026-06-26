# AuditIQ — Product Requirements Document (PRD)

| | |
|---|---|
| **Product** | AuditIQ — AI-Powered Forensic Audit Intelligence |
| **Version** | Draft v0.1 |
| **Status** | Draft |
| **Date** | 2026-06-25 |
| **Owner** | Product & Engineering |
| **Related docs** | [TECH_ARCHITECTURE](./TECH_ARCHITECTURE.md) · [FUNCTIONAL_SPEC](./FUNCTIONAL_SPEC.md) · [TEST_PLAN](./TEST_PLAN.md) |

---

## 1. Executive summary & vision

AuditIQ turns a company's annual-report PDF into a structured forensic risk assessment in
seconds. It combines a **deterministic analytical core** — the same quantitative models
professional auditors and analysts use (Beneish M-Score, Altman Z-Score, Benford's Law,
ratio benchmarking) — with an **AI layer** built on Anthropic's Claude that handles the
messy parts: reading financial statements out of a PDF, cross-referencing recent news, and
writing a plain-English summary.

**Vision.** Make first-pass forensic screening fast, consistent, and explainable, so that a
human professional can spend their time on judgement rather than on extracting numbers and
recomputing textbook ratios. AuditIQ is explicitly a *screening assistant*, not an opinion-
issuing auditor.

**Today's reality (grounded in the code).** AuditIQ is a single-user, locally-run Streamlit
application. The deterministic engines run with no API key; AI features require
`ANTHROPIC_API_KEY` and degrade gracefully when it is missing. An offline **demo mode**
(`auditiq/sample_data.py`) lets anyone explore the full dashboard with no key and no
network.

## 2. Problem statement & background

First-year auditors, forensic analysts, and credit/investment analysts spend significant
manual effort on the *same* early-stage tasks for every entity they look at:

- Keying figures out of a long PDF into a spreadsheet.
- Recomputing standard ratios and comparing them against a sector "feel" they hold in their
  heads rather than a documented benchmark.
- Remembering and correctly applying fraud/distress models (Beneish, Altman) and digit tests
  (Benford), which are error-prone to compute by hand and easy to mis-parameterise (wrong
  Altman variant, wrong threshold).
- Searching the web for recent governance/fraud news and trying to weigh it.

This manual work is slow, inconsistent between people, and hard to audit. AuditIQ
standardises it: a fixed, documented pipeline produces the same screening output for the
same inputs, with every score traceable to a formula and a threshold.

**Why now.** LLMs can reliably extract structured financials from semi-structured PDF text
and synthesise narrative findings, which removes the most tedious and least value-adding part
of the workflow while leaving the quantitative judgement in deterministic, testable code.

## 3. Goals & non-goals

### 3.1 Goals

| # | Goal |
|---|------|
| G1 | Convert annual-report PDFs into structured financials with minimal manual keying. |
| G2 | Produce consistent, explainable forensic scores (Beneish, Altman, Benford) with documented formulas and thresholds. |
| G3 | Benchmark a company's ratios against sector averages and surface deviations. |
| G4 | Support up-to-three-year trend analysis and a direction-of-travel verdict. |
| G5 | Cross-reference recent news for governance/fraud signals (when AI is enabled). |
| G6 | Synthesise everything into prioritised findings, an overall risk rating, and an AI narrative. |
| G7 | Export a professional, shareable PDF report. |
| G8 | Degrade gracefully without an API key (deterministic core + demo mode still work). |
| G9 | Keep the quantitative core deterministic and unit-testable offline. |

### 3.2 Non-goals (current release)

- **Not** an audit opinion or assurance engagement; outputs are screening estimates.
- **Not** a multi-tenant SaaS with accounts, roles, or persistence beyond local disk.
- **Not** a data warehouse — there is no database; state lives in `st.session_state` and the
  local `data/` folder.
- **Not** a real-time market-data or filings-ingestion service (no EDGAR/Companies House
  connector; PDFs are user-supplied).
- **Not** a fully localised product today — see §6 (internationalization) and the i18n gap
  analysis in [TEST_PLAN](./TEST_PLAN.md).

## 4. Target users & personas

| Persona | Description | Primary jobs-to-be-done |
|---------|-------------|-------------------------|
| **External auditor** (first/second year) | Big-4 or mid-tier audit staff doing planning-stage risk assessment. | Quickly flag manipulation/going-concern risk; get a documented benchmark; produce a sharable summary for seniors. |
| **Forensic analyst** | Investigates suspected fraud / earnings management. | Run Beneish + Benford; identify which indicators drive a manipulator verdict; cross-reference news. |
| **Credit / investment analyst** | Assesses counterparty or investee health. | Bankruptcy risk (Altman), leverage/liquidity vs sector, multi-year direction of travel. |
| **Finance student / educator** | Learning forensic-accounting models. | See the textbook models computed end-to-end on a real report; explore via demo mode with no setup. |

## 5. User stories & acceptance criteria

Stories use **Given / When / Then** acceptance criteria. IDs (US-n) are referenced by the
traceability matrix in [TEST_PLAN](./TEST_PLAN.md).

**US-1 — Upload and analyse reports**
*As an auditor, I want to upload up to three annual-report PDFs and run an analysis.*
- Given a valid API key, when I upload 1–3 PDFs and click **Run analysis**, then AuditIQ
  extracts financials, scores them, and switches to the results view.
- Given I upload 0 files, when I click Run analysis, then I see an error asking for at least
  one PDF.
- Given I upload more than 3 files, when I click Run analysis, then I see an error capping the
  upload at 3.
- Given no API key, then the **Run analysis** button is disabled and I am pointed to demo
  mode.

**US-2 — Explore without a key (demo mode)**
*As any user, I want to explore the full dashboard with no API key or PDF.*
- Given no key, when I click **Load sample data**, then a complete report for "Northgate
  Retail Group" (2021–2023) renders with all tabs populated, including a Benford chart.

**US-3 — See earnings-manipulation risk**
*As a forensic analyst, I want a Beneish M-Score and to know which indicators drive it.*
- Given two consecutive years, when I open the Beneish tab, then I see the M-Score, the
  manipulator verdict against the −1.78 threshold, the probit-implied probability, and each
  of the eight components with elevated ones highlighted.
- Given only one year, then the Beneish tab explains it needs a prior year.

**US-4 — See bankruptcy risk**
*As a credit analyst, I want an Altman Z-Score with the correct model variant.*
- Given sufficient balance-sheet data, when I open the Altman tab, then I see the Z-Score, the
  auto-selected model variant (original / private / emerging), the zone (Safe/Grey/Distress),
  and the X-components.
- Given insufficient balance-sheet data, then the tab explains what is missing.

**US-5 — Detect digit manipulation**
*As a forensic analyst, I want a Benford's Law test on the report's numbers.*
- Given an uploaded PDF (or demo population), when I open the Benford tab, then I see the
  observed-vs-expected first-digit distribution, MAD, chi-square + p-value, conformity band,
  and a suspicious/clear verdict.
- Given fewer than 50 numbers, then the result is annotated as not statistically meaningful
  and is never flagged "suspicious".

**US-6 — Benchmark against industry**
*As an analyst, I want company ratios compared to my chosen sector.*
- Given an industry selection, when I open the Benchmarking tab, then I see company vs
  industry for each benchmarked metric with a status flag.

**US-7 — Compare years**
*As an analyst, I want a multi-year trend and a direction verdict.*
- Given 2–3 years, when I open the Trends tab, then I see revenue/net-income, M-Score over
  time, a direction-of-travel verdict, and explanatory notes.
- Given one year, then the tab explains that 2–3 years are needed.

**US-8 — Cross-reference news**
*As an auditor, I want recent governance/fraud news sentiment.*
- Given a key with web search and a detected company name, when analysis runs, then the News
  tab shows sentiment score/label, a summary, signals, and up to six articles.
- Given no key or a failed call, then the News tab explains the feature requires the API and
  the rest of the report is unaffected.

**US-9 — Read a plain-English summary**
*As a junior auditor, I want a senior-style narrative.*
- Given a key, when analysis completes, then the Overview tab shows a 3–4 sentence AI summary
  leading with the most important risk.
- Given no key, then no summary block is shown and quantitative findings still render.

**US-10 — Export a PDF report**
*As an auditor, I want a shareable PDF of the full analysis.*
- Given a report, when I click **Generate PDF report** then **Download**, then I receive a
  branded PDF with cover/risk badge, summary, metrics, findings, Beneish table, Benford chart,
  benchmarks, trend chart, news, methodology, and disclaimer.

## 6. Functional requirements (mapped to the 10 capabilities)

Priorities use **MoSCoW** (Must / Should / Could / Won't-for-now). "Module" points to the
implementing source.

| FR | Capability | Requirement | Priority | Module |
|----|-----------|-------------|----------|--------|
| FR-1 | PDF upload & extraction | Accept 1–3 PDFs; extract text+tables; isolate statement pages; respect page cap. | Must | `extraction/pdf_reader.py` |
| FR-2 | AI structured extraction | Use Claude to extract a strict-schema `FinancialStatement` per year. | Must | `extraction/ai_extractor.py` |
| FR-3 | Red-flag detection | Synthesise findings across all engines + textual red flags; order high→medium; compute overall risk. | Must | `analysis/findings.py` |
| FR-4 | Beneish M-Score | 8-factor probit M-Score, manipulator threshold −1.78, probit probability, elevated components. Needs a prior year. | Must | `analysis/beneish.py` |
| FR-5 | Benford's Law | First-digit distribution, chi-square, MAD, Nigrini conformity bands, suspicious logic, min-sample note. | Must | `analysis/benford.py` |
| FR-6 | Altman Z-Score | Three variants with auto-selection and zone classification. | Must | `analysis/altman.py` |
| FR-7 | Industry benchmarking | Compare ratios to sector averages with per-metric severity flags. | Must | `analysis/benchmark.py`, `analysis/ratios.py`, `data/industry_benchmarks.json` |
| FR-8 | Up-to-3-year comparison | Build trend points + direction heuristic with tolerances. | Should | `analysis/comparison.py` |
| FR-9 | News-sentiment cross-reference | Claude + server-side `web_search_20250305`; sentiment, signals, articles; graceful failure. | Should | `intelligence/news.py` |
| FR-10 | AI narrative summary | Senior-auditor narrative leading with top risk; '' when no key. | Should | `intelligence/summary.py` |
| FR-11 | Professional PDF report | reportlab report with charts, branding, methodology, disclaimer. | Must | `reporting/pdf_report.py` |
| FR-12 | Interactive dashboard | Sidebar, upload vs results views, eight tabs, metric cards, demo mode, session state. | Must | `app.py` |
| FR-13 | Graceful degradation | Deterministic core + demo mode work with no key; AI features no-op safely. | Must | `config.py`, `intelligence/*` |
| FR-14 | Configurable models & limits | Env-driven model names and page cap via `Settings`. | Should | `config.py` |

## 7. Non-functional requirements

### 7.1 Performance
- A typical 1–3 PDF analysis should complete in seconds for the deterministic core; total
  latency is dominated by Claude calls (extraction per year, optional news, optional summary).
- PDF scanning is bounded by `AUDITIQ_MAX_PDF_PAGES` (default **60**) and extraction prompt
  text is truncated to the first **15,000** characters to bound token cost.
- Benchmark JSON is cached (`lru_cache`) so repeated benchmarking does not re-read disk.

### 7.2 Security & privacy
- Uploaded PDFs may contain **confidential financial information**; in upload mode their text
  is sent to the Anthropic API for extraction and (company name only) for news. This must be
  disclosed to users.
- Persistence is **local only** (`data/uploads`, `data/reports`); there is no server-side
  storage or multi-tenant data sharing.
- The API key is read from `.env` / environment and never written to disk by the app.
- No code execution on uploaded content; PDFs are parsed for text/tables only.

### 7.3 Reliability
- The pipeline is deterministic and pure (no network) so results are reproducible and
  testable offline.
- AI calls are wrapped so failures return safe defaults (`None`/`''`) rather than crashing the
  app; the upload handler also surfaces extraction errors to the user without losing state.

### 7.4 Usability
- Single-screen flow: upload landing → results with tabs. Metric cards use traffic-light
  colours. Demo mode requires zero setup.

### 7.5 Accessibility
- Dark-navy theme with colour-coded risk. **Gap:** colour is currently the primary signal in
  several places (metric cards, flags); text labels exist alongside but contrast/colour-blind
  affordances are not formally verified. Tracked as an open question.

### 7.6 Internationalization (i18n) / localization (l10n)
- A `currency` field is captured per statement, but the UI and PDF **hard-code unit glyphs**
  (`%`, `x`, `d`) and assume Anglo number formatting; there is no currency symbol rendering,
  no locale-aware number parsing, and no string externalization/translation layer.
- `benford.extract_numbers` assumes `,` as the thousands separator and `.` as the decimal
  separator; European (`1.234,56`), Indian grouping (`12,34,567`), and space-separated
  formats are **not** handled correctly.
- This is a known limitation and a priority for future work. See the i18n/l10n section of
  [TEST_PLAN](./TEST_PLAN.md) for the required future test cases.

## 8. Success metrics / KPIs

| KPI | Target (initial) |
|-----|------------------|
| Extraction field coverage | ≥ 90% of core fields populated on well-structured reports. |
| Analysis latency (deterministic core) | < 2 s per report (excluding LLM calls). |
| End-to-end latency (with AI) | < ~60 s for 3 years including extraction + news + summary. |
| False-positive rate on manipulator verdict | Monitored; minimise via threshold + documented drivers. |
| Demo-mode success | 100% of tabs render with no key/network. |
| Report generation success | 100% for any valid in-memory report. |
| Test pass rate | 15/15 unit tests green in CI. |

## 9. Assumptions, dependencies & constraints

**Assumptions**
- Users supply machine-readable PDFs (text extractable; not pure scans). Scanned/image-only
  PDFs are out of scope (no OCR).
- Figures in a report are stated in a single reporting currency, in millions or scalable to
  millions by the model.

**Dependencies**
- Anthropic API (`anthropic` SDK) and a valid `ANTHROPIC_API_KEY` for AI features.
- Anthropic **server-side web search** (`web_search_20250305`) enabled on the account for
  news sentiment.
- Python 3.12 runtime (`.venv`); libraries per `requirements.txt` (Streamlit, pdfplumber,
  pydantic v2, scipy, pandas/numpy, plotly, matplotlib, reportlab).

**Constraints**
- Single-user, local execution; no auth/multi-tenancy.
- PDF page cap (60) and prompt truncation (15k chars) bound extraction completeness.
- Extraction accuracy is model-dependent and can introduce error into all downstream scores.

## 10. Risks & mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **False positives** (manipulator/distress flags) | Reputational; wasted investigation | Medium | Documented thresholds; show driver components; "screening only" framing; human review required. |
| **Extraction error from PDF** | Wrong inputs → wrong scores | Medium | Strict JSON schema; truncation/page-cap disclosed; report disclaimer notes possible extraction error. |
| **Model cost / latency** | Budget overrun; slow UX | Medium | Sonnet default; page cap; 15k-char truncation; bounded `max_tokens`. |
| **Confidential data exposure** | Privacy/legal | Medium | Disclose that PDFs are sent to Claude; local-only persistence; no third-party storage. |
| **Prompt injection via PDF/news text** | Manipulated extraction/summary | Low–Medium | Strict "return only JSON" prompts; tolerant JSON parsing; outputs are advisory and human-reviewed. (See security tests in [TEST_PLAN](./TEST_PLAN.md).) |
| **Legal misuse as an audit opinion** | Liability | Medium | Prominent disclaimer in UI and PDF: *not a substitute for qualified audit advice*. |
| **Web search unavailable** | No news section | Medium | News returns `None`; UI explains; rest of report unaffected. |
| **i18n/number-format errors** | Mis-parsed non-Anglo figures | Medium | Documented limitation; future locale-aware parsing + tests. |

## 11. Out-of-scope & roadmap

**Out of scope (now):** OCR for scanned PDFs; multi-tenant accounts/roles; persistent
database; direct filings ingestion (EDGAR/Companies House); full localisation; XBRL parsing.

**Roadmap (indicative)**
- **Near term:** locale-aware number parsing and currency rendering; string externalization
  for UI/PDF; broaden sector benchmarks; surface the 5-variable Beneish threshold (currently
  defined but unused — see [FUNCTIONAL_SPEC](./FUNCTIONAL_SPEC.md)).
- **Mid term:** OCR fallback; configurable benchmark sets; richer evidence linking (page
  references for extracted figures); accessibility/contrast audit.
- **Longer term:** multi-user deployment (containerise / Streamlit Cloud); persistence;
  filings connectors.

## 12. Open questions

1. Should the **5-variable Beneish** model (threshold `−2.22`, defined in `config.py`) be
   exposed, given the 8-variable model is the only one currently computed?
2. Should `inventory_days` and `revenue_growth` (computed in `ratios.py`) be added to the
   benchmark table (currently only six ratios are benchmarked)?
3. What is the data-retention policy for `data/uploads` and `data/reports` (currently no
   automatic cleanup)?
4. Which currencies/locales are first-priority for i18n?
5. Should news/summary be opt-in per analysis to control cost and data egress?

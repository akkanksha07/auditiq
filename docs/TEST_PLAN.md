# AuditIQ — Test Plan

| | |
|---|---|
| **Product** | AuditIQ — AI-Powered Forensic Audit Intelligence |
| **Version** | Draft v0.1 |
| **Status** | Draft |
| **Date** | 2026-06-25 |
| **Audience** | QA, engineers |
| **Related docs** | [README](./README.md) · [PRD](./PRD.md) · [TECH_ARCHITECTURE](./TECH_ARCHITECTURE.md) · [CODE_MAP](./CODE_MAP.md) · [FUNCTIONAL_SPEC](./FUNCTIONAL_SPEC.md) |

---

## 1. Strategy & scope

AuditIQ is a layered Python 3.12 / Streamlit application with a **deterministic analytical
core** and an **AI layer** that degrades gracefully without `ANTHROPIC_API_KEY`. The testing
strategy follows that seam:

- **The deterministic core is the priority for automated testing** — it is pure, network-free,
  and fully reproducible (ratios, Beneish, Benford, Altman, benchmarking, findings, comparison,
  `pipeline.build_report`). The existing **15 unit tests** all target this core.
- **The AI layer is tested with a mocked Anthropic client** — extraction, news, and summary
  must never hit the live API in CI. We assert on prompt construction, JSON tolerance, schema
  validation, and graceful failure.
- **The UI is tested with `streamlit.testing.v1.AppTest`** for boot/demo/upload flows, and
  optionally **Playwright** for true end-to-end browser checks.
- **i18n/l10n is currently a gap** and is documented here as a gap analysis plus the required
  future cases (multi-currency, non-Anglo number parsing, dates, Unicode, RTL, string
  externalization).

**In scope:** unit, integration, functional/acceptance (per PRD requirement), e2e/UI,
i18n/l10n (gap), performance, security, regression/smoke/UAT.
**Out of scope (matching product non-goals):** OCR accuracy, multi-tenant/auth, database
persistence, filings connectors, full localisation correctness (only readiness is assessed).

### Test levels at a glance
| Level | Target | Anthropic | Tooling | State today |
|---|---|---|---|---|
| Unit | Single functions in the core | not called | pytest | **15 tests, passing** |
| Integration | `build_report`, report generation, extraction+analysis | **mocked** | pytest + monkeypatch | to add |
| Functional / acceptance | PRD requirements end-to-end | mocked | pytest / AppTest | to add |
| E2E / UI | App boot, demo, upload flows | mocked | `AppTest`; Playwright (optional) | to add |
| i18n / l10n | Currency, number/date parsing, Unicode, RTL | mocked | pytest + AppTest | **gap** |
| Performance | Large/long PDFs, page cap, token budget, latency | mocked/measured | pytest-benchmark / manual | to add |
| Security | Confidential data, prompt injection, secrets | mocked | pytest + review | to add |

---

## 2. Environments & tooling

- **Runtime:** Python **3.12** in `.venv`. The system `python3` is a broken x86_64 Python 3.7 —
  **never use it.** All commands use the venv:
  - Tests: `.venv/bin/pytest -q` (config in `pytest.ini`: `pythonpath = .`, `testpaths = tests`, `addopts = -q`).
  - App: `.venv/bin/streamlit run app.py`.
- **No API key needed** for the core suite (and CI must run without one to prove graceful
  degradation). AI paths are exercised via mocks.
- **Suggested tooling additions**
  - `streamlit.testing.v1.AppTest` — headless Streamlit script runner for UI logic (sidebar,
    buttons, tabs, session_state) without a browser.
  - **Playwright** — optional true browser e2e (rendering, downloads, charts).
  - **`monkeypatch` / `unittest.mock`** — replace the Anthropic client. Mock at the **seam**:
    patch `auditiq.intelligence.llm.complete` (and/or `get_client`) so `ai_extractor`, `news`,
    and `summary` run against canned responses. This keeps tests offline and deterministic.
  - `pytest-cov` for coverage; `pytest-benchmark` (optional) for performance assertions.
  - A few small fixture PDFs (machine-readable, image-only, and a large multi-page one) under a
    `tests/fixtures/` directory (does not exist yet — see [§11](#11-test-data--fixtures)).

### Mocking the Anthropic client (pattern)
```python
# Example: extraction without the network.
import auditiq.intelligence.llm as llm

def test_extract_financials_mocked(monkeypatch):
    canned = '{"companyName":"Acme","revenue":100,"netIncome":10}'
    monkeypatch.setattr(llm, "complete", lambda *a, **k: canned)
    from auditiq.extraction.ai_extractor import extract_financials
    fs = extract_financials("…report text…", year_label="2023")
    assert fs.company_name == "Acme" and fs.revenue == 100 and fs.year == "2023"
```

---

## 3. Unit tests — existing inventory (15)

All run via `.venv/bin/pytest`, no key, against the deterministic core. Counts confirmed from
source.

### `tests/test_beneish.py` → `analysis/beneish.py` (3)
| Test | Asserts |
|---|---|
| `test_returns_none_without_prior` | `compute_beneish(year, None) is None`. |
| `test_identical_clean_years_known_score` | Two identical clean years → `M ≈ -2.48`, not manipulator, `0 ≤ probability ≤ 5`, the 8 component keys present, `TATA == 0.0`. |
| `test_sample_latest_year_is_elevated` | Sample 2023 vs 2022 → `m_score > threshold`, `is_manipulator is True`. |

### `tests/test_benford.py` → `analysis/benford.py` (4)
| Test | Asserts |
|---|---|
| `test_expected_distribution_sums_to_one` | `sum(EXPECTED) ≈ 1.0`; `EXPECTED[1]·100 ≈ 30.1`. |
| `test_first_digit` | `first_digit` on `0.0123→1`, `-540→5`, `98765→9`, `0→None`. |
| `test_extract_numbers_handles_formats` | `"1,234.5"→1234.5`, `"(567)"→-567`, `"£89"→89` parsed (Anglo formats). |
| `test_conforming_vs_nonconforming` | 60 nines → `nonconformity`, `suspicious`; small sample (5) → not suspicious, `note` set. |

### `tests/test_altman.py` → `analysis/altman.py` (4)
| Test | Asserts |
|---|---|
| `test_model_auto_selection` | retail→`emerging`; manufacturer with market value→`original`; manufacturer without→`private`. |
| `test_healthy_firm_is_safe` | Healthy firm → zone `low`, label "Safe". |
| `test_distressed_firm_is_high_risk` | Distressed firm → zone `high`. |
| `test_missing_data_returns_none` | Statement with only revenue → `None`. |

### `tests/test_ratios_benchmark.py` → `analysis/ratios.py` + `analysis/benchmark.py` (3)
| Test | Asserts |
|---|---|
| `test_ratios_on_sample` | Sample 2023: receivables days `≈ 5000·365/56000`, gross margin `≈ 15000/56000`, current ratio `== 0.8`. |
| `test_benchmark_flags` | Current Ratio (<1.0) → high; Receivables Days (>1.3× benchmark) → high. |
| `test_benchmarks_data_integrity` | `industries()` keys == JSON keys; each sector has the 4 core metric keys. |

### `tests/test_pipeline.py` → `pipeline.py` (1)
| Test | Asserts |
|---|---|
| `test_build_report_offline` | Sample report: company name, 3 years, year 0 no Beneish / latest has Beneish+Altman, comparison with 3 points + valid direction, overall risk medium/high, latest year has a non-"clear" finding. |

**Total: 15.**

### Unit gaps to close (recommended new cases)
| Module | Gap | Suggested cases (given / when / then) |
|---|---|---|
| `ratios.py` | Edge cases not directly tested. | Given a statement with `cogs=None` and `revenue=100`, when `compute_ratios`, then `inventory_days` uses `0.7·revenue` (not `None`). Given `interest_expense=0`, then `interest_coverage is None`. Given `prior=None`, then `revenue_growth is None`. Given `debt_to_equity` with `total_debt=None`, then it falls back to `resolved_total_liabilities`. |
| `findings.py` | No direct tests for synthesis/ordering. | Given a manipulator Beneish + a high benchmark, when `build_findings`, then a high beneish finding precedes the high benchmark finding and `overall_risk == "high"`. Given all-benign inputs and no red flags, then exactly one `clear`/`low` finding. Given 6 red flags, then only the first 4 textual findings appear. |
| `comparison.py` | Only indirectly covered. | Given a rising M-score beyond 0.20, when `build_comparison`, then a worsening note and `direction` reflects it. Given fewer than 2 years, then `None`. Given net-income improvement, then it counts toward `better` but adds no note (asymmetry, per FUNCTIONAL_SPEC §10). |
| `benford.py` | Anglo-only extraction is implicitly asserted but the European/Indian failures are not pinned. | Add **xfail** cases documenting `"1.234,56"` and `"12,34,567"` mis-parsing (see [§7 i18n](#7-i18n--l10n-gap-analysis--required-cases)). |
| `llm.extract_json` | Not directly tested. | Given a fenced ```` ```json {…}``` ```` string, then parses the object. Given prose around an object, then the regex fallback extracts it. Given a bare array, then parses the list. Given invalid JSON with no object/array, then raises. |
| `news.py` parsing | Pure parsing branch is testable with a stubbed `complete`. | Given canned JSON, then `NewsSentiment` built; label derived from score when absent; invalid articles skipped; non-string flags dropped. Given a non-dict response, then `None`. |
| `models.py` | Derived props untested. | Given assets+equity but no `total_liabilities`, then `resolved_total_liabilities == assets − equity`. Given revenue+cogs but no `grossProfit`, then `resolved_gross_profit == revenue − cogs`. Given camelCase JSON, then aliases populate snake_case attributes and unknown keys are ignored. |

---

## 4. Integration tests

Exercise multiple modules together; AI is mocked.

| ID | Scenario | Given / When / Then |
|---|---|---|
| INT-1 | Offline `build_report` end-to-end | Given the sample statements, when `build_report(..., industry="retail")`, then 3 `YearAnalysis`, a `Comparison`, and `overall_risk ∈ {medium, high}` (extends the existing pipeline test with explicit per-year findings/benchmark assertions). |
| INT-2 | Report generation from a built report | Given a built `AuditReport`, when `report_bytes(report)`, then non-empty bytes beginning with `%PDF`; when `generate_report(report)`, then a file is written under `data/reports` with the sanitised name. |
| INT-3 | PDF report with no Benford/news/summary | Given a report with `summary=""`, `news=None`, single year (no comparison), when `report_bytes`, then it succeeds (cover + summary placeholder + metrics + methodology) without raising. |
| INT-4 | Extraction → analysis with a mocked client | Given canned extraction JSON for 2 years (via patched `llm.complete`), when extracting both then `build_report`, then Beneish is computed for the later year and the report assembles. |
| INT-5 | `analyze_year` wiring | Given a statement + prior + a Benford text, when `analyze_year`, then ratios, benchmarks, beneish, altman, benford, and findings are all populated consistently. |
| INT-6 | Benford on `full_text` vs `financial_text` | Given a `PdfContent`, when `run_analysis`-style wiring, then the Benford text used is `full_text` (documents the §15.3 behaviour). |

---

## 5. Functional / acceptance tests (per PRD requirement)

Mapped to PRD user stories (US-n) and functional requirements (FR-n). AI mocked.

| ID | PRD ref | Given / When / Then |
|---|---|---|
| ACC-1 | US-1 / FR-1,2 | Given a key and 1–3 PDFs (mocked extraction), when Run analysis, then financials are extracted, scored, and the results view renders. |
| ACC-1a | US-1 | Given 0 files, when Run analysis, then an error asks for at least one PDF; given >3 files, then an error caps at 3; given no key, then the button is disabled. |
| ACC-2 | US-2 / FR-13 | Given no key, when Load sample data, then a full "Northgate Retail Group" (2021–2023) report renders with all tabs incl. a Benford chart. |
| ACC-3 | US-3 / FR-4 | Given two years, when opening Beneish, then M-score, manipulator verdict vs −1.78, probit probability, and 8 components (elevated highlighted) show; given one year, then the "needs a prior year" info shows. |
| ACC-4 | US-4 / FR-6 | Given sufficient balance-sheet data, when opening Altman, then Z-score, auto-selected variant, zone, and X-components show; given insufficient data, then the info state. |
| ACC-5 | US-5 / FR-5 | Given an uploaded/demo population, when opening Benford, then observed-vs-expected, MAD, χ²+p, conformity, verdict; given <50 numbers, then annotated and never "suspicious". |
| ACC-6 | US-6 / FR-7 | Given an industry, when opening Benchmarking, then company-vs-industry rows with flags. |
| ACC-7 | US-7 / FR-8 | Given 2–3 years, when opening Trends, then revenue/net-income, M-score over time, direction, and notes; given one year, then the info state. |
| ACC-8 | US-8 / FR-9 | Given a key + web search + a company name (mocked), when analysis runs, then News shows score/label/summary/signals/articles; given no key/failure, then the info state and the rest of the report is unaffected. |
| ACC-9 | US-9 / FR-10 | Given a key (mocked summary), when analysis completes, then Overview shows a 3–4 sentence summary; given no key, then no summary block but findings still render. |
| ACC-10 | US-10 / FR-11 | Given a report, when Generate PDF then Download, then a branded PDF with all sections + disclaimer is produced. |
| ACC-11 | FR-14 | Given env overrides (`AUDITIQ_*`), when settings load, then the model names / page cap reflect them. |

---

## 6. End-to-end / UI tests

Using `AppTest` (headless) for logic; Playwright (optional) for rendering/downloads. Anthropic mocked.

| ID | Flow | Given / When / Then |
|---|---|---|
| E2E-1 | App boot | Given no report in session, when the app runs, then the landing hero + upload view render and the sidebar shows industry + key status. |
| E2E-2 | Demo flow | Given no key, when "Load sample data" is clicked, then `session_state["report"]` is set and the results view with 8 tabs renders; each tab renders without exception. |
| E2E-3 | Upload flow (mocked AI) | Given a key (mocked `complete`) and a fixture PDF, when Run analysis, then the report is built and shown; verify the status steps appear. |
| E2E-4 | Validation | Given 0 / >3 files, when Run analysis, then the corresponding `st.error` appears and the view stays on landing. |
| E2E-5 | Clear | Given a report, when "Clear" is clicked, then session state resets to landing. |
| E2E-6 | Year selector | Given a 3-year report, when a different year is selected, then the per-year tabs reflect that year. |
| E2E-7 | PDF download (Playwright) | Given a report, when Generate then Download, then a PDF file is delivered. |
| E2E-8 | No-key gating | Given no key, then Run analysis is disabled and the demo-mode hint is visible. |

---

## 7. i18n / l10n gap analysis & required cases

**Status: this is currently a GAP.** AuditIQ assumes Anglo currency/number/date conventions
end-to-end and has no string-externalization layer. The cases below are the **required future
tests**; several should be added now as `xfail`/`skip` to document current behaviour and guard
the eventual fix. See [FUNCTIONAL_SPEC §15.10](./FUNCTIONAL_SPEC.md) for the as-built behaviour.

### 7.1 Multi-currency (GBP / USD / EUR and beyond)
- **Current:** `FinancialStatement.currency` is captured but never rendered; the UI/PDF hard-code
  unit glyphs `%`, `x`, `d` and show bare numbers (in millions) with no currency symbol.
- **Required cases:** Given statements in GBP / USD / EUR / JPY / INR, when rendered, then the
  reporting currency is shown consistently in cards, benchmark tables, and the PDF; mixed-currency
  inputs across years are detected and surfaced (today they silently coexist).

### 7.2 Number parsing in `benford.extract_numbers`
The regex assumes `,` = thousands and `.` = decimal. Required cases (expected to **fail today**):
| Format | Example | Expected value | Today |
|---|---|---|---|
| European | `1.234,56` | 1234.56 | mis-parsed (treats `.` as thousands, `,` ignored). |
| Indian grouping | `12,34,567` | 1234567 | mis-grouped. |
| Space separator | `1 234 567,89` | 1234567.89 | split into separate tokens. |
| Parenthetical negative | `(1,234)` | -1234 | **handled** (regression-guard it). |
| Currency-prefixed | `£89`, `$1,000`, `€1.000` | 89 / 1000 / (1000) | first two handled; `€1.000` mis-parsed. |

Add these as documented `xfail` until locale-aware parsing lands; flip to passing with the fix.

### 7.3 Decimal / thousands separators (general)
- **Required:** a locale-aware parser (or a per-document locale hint from extraction) that
  normalises separators before Benford and before any numeric display.

### 7.4 Date formats
- **Current:** `as_of` / `generated_at` use fixed `%Y-%m-%d` / `%Y-%m-%d %H:%M`; news article
  dates are passed through unparsed.
- **Required:** validate/normalise article dates; render dates per a chosen locale.

### 7.5 Unicode / non-Latin company names
- **Current:** names flow through to UI and prompts unmodified; the PDF **filename** sanitiser
  keeps only `[A-Za-z0-9 _-]`, so a non-Latin name collapses toward the `report` default on disk
  (the in-document title is unaffected).
- **Required cases:** Given a company named `株式会社テスト` or `Société Générale`, when rendering,
  then the dashboard and PDF body display it correctly; when saving, then the on-disk filename is
  a reasonable transliteration/slug rather than `report`.

### 7.6 RTL readiness
- **Current:** layout and the PDF assume LTR.
- **Required:** verify the dashboard and PDF render acceptably for RTL company names / summaries
  (Arabic/Hebrew), at least without corruption.

### 7.7 String-externalization readiness (UI + PDF)
- **Current:** all strings are hard-coded English in `app.py` and `pdf_report.py`.
- **Required:** extract user-facing strings into a catalog (e.g. a message dict / gettext) so the
  UI and PDF can be localised; add a smoke test that swaps the catalog and asserts no missing keys.

---

## 8. Performance tests

| ID | Concern | Given / When / Then |
|---|---|---|
| PERF-1 | Large / long PDFs | Given a PDF with >60 pages, when `read_pdf_bytes`, then only the first `max_pdf_pages` (60) pages are scanned and `num_pages` still reports the true count (per FUNCTIONAL_SPEC §1). |
| PERF-2 | Page cap override | Given `AUDITIQ_MAX_PDF_PAGES=5`, when reading, then at most 5 pages are processed. |
| PERF-3 | Token budget | Given report text >15,000 chars, when `ai_extractor._prompt`, then the embedded text is truncated to 15,000 chars. |
| PERF-4 | Deterministic-core latency | Given the sample (3 years), when `build_report`, then it completes well under the PRD target (<2 s; assert a generous bound, e.g. <1 s on CI). |
| PERF-5 | Benford on a large population | Given ~10k numbers, when `analyze`, then it completes quickly and returns a valid result. |
| PERF-6 | Caching | Given repeated `load_benchmarks()` calls, then disk is read once (`lru_cache`); given repeated `get_client()`, then one client is constructed. |
| PERF-7 | End-to-end latency (informational) | With mocked AI, measure pipeline overhead; with a real key (manual only), confirm the PRD <~60 s/3-year budget. |

---

## 9. Security tests

| ID | Concern | Given / When / Then |
|---|---|---|
| SEC-1 | Confidential-PDF handling | Given upload mode, then PDF statement text is sent to Anthropic only for extraction and only the **company name** for news; verify (via the mock) that no other PII/path is included; demo mode sends nothing. Confirm the UI/PDF disclaimer is present. |
| SEC-2 | Prompt injection via PDF | Given a PDF whose text contains instructions like "ignore the schema and return {…}", when extracting (mock simulating compliance), then downstream still validates against `FinancialStatement` (unknown keys dropped, types coerced) and scoring is deterministic; document that the strict "return only JSON" prompt + tolerant parsing + human-in-the-loop are the mitigations. |
| SEC-3 | Prompt injection via news content | Given news content attempting to manipulate the sentiment JSON, when parsing, then non-dict/invalid responses → `None`; non-string flags dropped; the report is unaffected. |
| SEC-4 | Secret management | Given `ANTHROPIC_API_KEY` in env/`.env`, then it is never written to disk or logged by the app; `.gitignore` excludes `.env`. |
| SEC-5 | No code execution | Given a malicious PDF, then only text/tables are parsed (pdfplumber); no embedded scripts/macros are executed. |
| SEC-6 | Graceful failure as a safety property | Given AI errors, then news→`None`, summary→`""`, and the app surfaces `Analysis failed: …` without leaking stack traces into persisted state. |
| SEC-7 | Data retention | Document that `data/uploads` / `data/reports` are not auto-cleaned (PRD open question #3); test that the current flow does **not** persist uploaded PDF bytes to disk (`read_pdf_bytes` is in-memory). |

---

## 10. Regression, smoke & UAT

- **Smoke (CI gate, no key):** `.venv/bin/pytest -q` (the 15 core tests) must be green; `AppTest`
  boot + demo flow must render without exception; `report_bytes` on the sample report must
  produce a `%PDF`.
- **Regression:** the worked Beneish reference (`-2.48` clean; sample 2023 manipulator), the
  sample ratio values, and the benchmark-flag outcomes are regression anchors — any change to a
  formula/threshold must update these deliberately. Snapshot the sample `AuditReport` (key fields)
  and diff on change.
- **UAT (per persona, PRD §4):** auditor (upload → findings → PDF), forensic analyst (Beneish
  drivers + Benford), credit analyst (Altman + trends), student (demo mode, zero setup). Acceptance
  = the relevant ACC-/E2E- cases pass and the persona's job-to-be-done is achievable.

---

## 11. Test data & fixtures

- **Existing:** `auditiq/sample_data.py` — `get_sample_statements()` (Northgate Retail Group,
  2021–2023; crafted to surface an elevated Beneish + mixed flags) and
  `get_sample_benford_numbers()` (400 Benford-conforming values). These back most core tests and
  demo mode.
- **Needed (does not exist yet):** a `tests/fixtures/` directory with small sample **PDFs**:
  1. a machine-readable annual report (for extraction/Benford integration),
  2. an image-only/scanned PDF (to assert graceful empty-text behaviour, no OCR),
  3. a large multi-page PDF (>60 pages) for the page-cap performance case,
  4. a PDF containing European/Indian-formatted numbers (for the i18n cases),
  5. a PDF with a non-Latin company name (Unicode/filename cases).
- **Mock payloads:** canned extraction JSON, news JSON (valid + malformed + non-dict), and
  summary text strings for the AI-path tests.

---

## 12. Coverage goals & CI

- **Coverage goals:** deterministic core (`analysis/*`, `ratios`, `benchmark`, `pipeline`,
  `models` derived props) **≥ 90% line coverage**; AI layer (`ai_extractor`, `news`, `summary`,
  `llm.extract_json`) **≥ 80%** via mocks; UI smoke (`AppTest`) covering boot/demo/upload paths.
- **CI recommendation:** GitHub Actions on Python 3.12; create the venv, `pip install -r
  requirements.txt`, run `pytest -q --cov=auditiq` **with no `ANTHROPIC_API_KEY`** (proving the
  core + graceful degradation), then the `AppTest` smoke job. Gate merges on green + the coverage
  thresholds. Optional nightly Playwright e2e and a manual, opt-in job that runs the AI paths
  against a real key (never on PRs).

---

## 13. Traceability matrix (requirements → tests)

PRD FR/US → existing unit tests and the new cases proposed above.

| PRD ref | Capability | Existing tests | New / planned cases |
|---|---|---|---|
| FR-1 / US-1 | PDF upload & extraction | — | PERF-1, PERF-2, E2E-3, ACC-1a |
| FR-2 / US-1 | AI structured extraction | — | INT-4, ACC-1, unit `extract_json`, PERF-3, SEC-2 |
| FR-3 / US-3,4,5 | Red-flag synthesis | `test_build_report_offline` (indirect) | findings unit cases, ACC-3..7 |
| FR-4 / US-3 | Beneish M-Score | `test_beneish.py` (3) | ratios/findings interplay, ACC-3 |
| FR-5 / US-5 | Benford's Law | `test_benford.py` (4) | i18n §7.2 (xfail), ACC-5, PERF-5 |
| FR-6 / US-4 | Altman Z-Score | `test_altman.py` (4) | ACC-4 |
| FR-7 / US-6 | Ratios + benchmarking | `test_ratios_benchmark.py` (3) | ratios edge cases, ACC-6 |
| FR-8 / US-7 | Multi-year comparison | `test_pipeline.py` (indirect) | comparison unit cases, ACC-7 |
| FR-9 / US-8 | News sentiment | — | news parsing unit, INT (mock), ACC-8, SEC-3 |
| FR-10 / US-9 | AI narrative summary | — | summary mock unit, ACC-9 |
| FR-11 / US-10 | PDF report | — | INT-2, INT-3, ACC-10, E2E-7 |
| FR-12 | Interactive dashboard | — | E2E-1..8, ACC-* |
| FR-13 / US-2 | Graceful degradation | `test_*` run with no key | ACC-2, SEC-6, E2E-2/8 |
| FR-14 | Configurable models & limits | — | ACC-11, PERF-2/3 |
| (PRD §7.6) | i18n / l10n | — | §7 cases (currently gap) |
| (PRD §7.2) | Security & privacy | — | SEC-1..7 |
| (PRD §7.1) | Performance | — | PERF-1..7 |

---

## 14. Known limitations of the test approach

- **No live-AI assertions in CI** — extraction/news/summary correctness against the real model is
  validated only by manual/opt-in runs; CI proves wiring, parsing tolerance, and graceful failure.
- **No fixture PDFs yet** — extraction/Benford integration and the page-cap/i18n/Unicode cases are
  blocked until `tests/fixtures/` is populated.
- **i18n is unimplemented** — the i18n cases are specified but most must be `xfail`/`skip` until the
  locale-aware parsing, currency rendering, and string-externalization work lands.
- **Accessibility/contrast** (PRD §7.5) is not automatically tested — colour is the primary signal
  in several places; a manual contrast/colour-blind audit is recommended.
- **AppTest coverage of HTML/CSS rendering is limited** — `AppTest` validates script logic and
  widget state, not visual rendering; Playwright is needed for true visual/e2e confidence.

---

*Cross-references:* [README](./README.md) · [PRD](./PRD.md) · [TECH_ARCHITECTURE](./TECH_ARCHITECTURE.md) · [CODE_MAP](./CODE_MAP.md) · [FUNCTIONAL_SPEC](./FUNCTIONAL_SPEC.md)

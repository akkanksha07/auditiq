# AuditIQ — Documentation Index

**Status:** Draft v0.1 · **Date:** 2026-06-25 · **Owner:** Product & Engineering

AuditIQ is an AI-powered forensic audit intelligence platform. Users upload annual-report
PDFs and receive an automated forensic risk assessment: red-flag detection, an earnings-
manipulation score (Beneish M-Score), a digit-manipulation test (Benford's Law), a
bankruptcy-risk score (Altman Z-Score), industry benchmarking, up-to-three-year trend
comparison, news-sentiment cross-reference, a professional PDF report, and an interactive
Streamlit dashboard.

> **Not a substitute for qualified audit advice.** AuditIQ is an analytical *screening*
> tool. Every score is a model estimate and must be reviewed by a qualified professional.

---

## Document set

| Document | Purpose | Audience |
|----------|---------|----------|
| [PRD.md](./PRD.md) | Product Requirements Document — vision, problem, personas, user stories, functional & non-functional requirements (MoSCoW), KPIs, risks, roadmap. | Product, stakeholders, eng leads |
| [TECH_ARCHITECTURE.md](./TECH_ARCHITECTURE.md) | Technical architecture — design principles, Mermaid diagrams (context, container, data-flow, sequence, class), tech stack, integrations, config & secrets, security/privacy, extensibility, deployment, and a code-map summary linking `CODE_MAP.md`. | Engineers, architects |
| [CODE_MAP.md](./CODE_MAP.md) | Authoritative per-file reference — every module, its public API, key behaviours, and how it connects to the rest of the system. The source of truth for code facts. | Engineers, reviewers, new contributors |
| [FUNCTIONAL_SPEC.md](./FUNCTIONAL_SPEC.md) | Functional specification — per-feature inputs, exact formulas/coefficients/thresholds, outputs, UI behaviour, edge cases, error states; the `FinancialStatement` data dictionary; locale handling as-built. | Engineers, QA, analysts |
| [TEST_PLAN.md](./TEST_PLAN.md) | Test strategy & cases — unit (the 15 existing tests mapped), integration, functional/acceptance, e2e/UI, **i18n/l10n gap analysis**, performance, security, regression/smoke/UAT, traceability matrix. | QA, engineers |

---

## Quick orientation

**Architecture in one line.** A *deterministic analytical core* (ratios, Beneish, Benford,
Altman, benchmarking, findings, comparison) that runs with no API key, wrapped by an
*AI layer* (PDF extraction, news sentiment, narrative summary) that requires
`ANTHROPIC_API_KEY` and degrades gracefully when it is absent. A Streamlit app (`app.py`)
drives the UI; `auditiq/pipeline.py` orchestrates the offline analysis.

**Two ways to run analysis.**

1. **Upload mode** — one to three PDFs → `pdf_reader` → `ai_extractor` (Claude) →
   `pipeline.build_report` → dashboard + downloadable PDF report. Requires an API key.
2. **Demo mode** — "Load sample data" builds a report from `auditiq/sample_data.py`
   (Northgate Retail Group, 2021–2023) with a synthetic Benford population. No API key,
   no network.

**Key reference files**

| Concern | File |
|---------|------|
| Settings, paths, thresholds | `auditiq/config.py` |
| Data models (pydantic v2) | `auditiq/models.py` |
| Offline orchestration | `auditiq/pipeline.py` |
| Dashboard (entry point) | `app.py` |
| Design source of truth | `prototype/` |
| Tests (15) | `tests/` |

## Conventions used across these docs

- **Monetary units:** all financial figures are in **millions** of the reporting currency.
- **Risk levels:** `low` / `medium` / `high` (see `config.RISK_LEVELS`).
- **Dates / status:** every document is dated **2026-06-25**, **Draft v0.1**.
- **Environment:** Python **3.12** in `.venv`. The system `python3` (x86_64 3.7) is broken
  and must not be used. Tests run with `.venv/bin/pytest`.
- Statements in these docs are grounded in the source as of this date; any place the code
  differs from prior product narrative is called out explicitly (see the "Known
  discrepancies" notes in [TECH_ARCHITECTURE.md](./TECH_ARCHITECTURE.md) and
  [FUNCTIONAL_SPEC.md](./FUNCTIONAL_SPEC.md)).

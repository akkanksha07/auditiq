"""Central configuration: paths, settings, models, and analysis constants."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
PKG_DIR = Path(__file__).resolve().parent
BASE_DIR = PKG_DIR.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
BENCHMARKS_PATH = PKG_DIR / "data" / "industry_benchmarks.json"

for _d in (DATA_DIR, UPLOAD_DIR, REPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ─── Runtime settings (env-driven) ────────────────────────────────────────────
@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None
    extraction_model: str = os.getenv("AUDITIQ_EXTRACTION_MODEL", "claude-sonnet-4-6")
    narrative_model: str = os.getenv("AUDITIQ_NARRATIVE_MODEL", "claude-sonnet-4-6")
    news_model: str = os.getenv("AUDITIQ_NEWS_MODEL", "claude-sonnet-4-6")
    max_pdf_pages: int = int(os.getenv("AUDITIQ_MAX_PDF_PAGES", "60"))

    @property
    def has_api_key(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()


# ─── Analysis constants ───────────────────────────────────────────────────────
# Beneish M-Score manipulator thresholds (Beneish, 1999).
BENEISH_THRESHOLD = -1.78          # 8-variable model
BENEISH_THRESHOLD_5VAR = -2.22     # 5-variable (conservative) model

# Altman Z-Score zone cutoffs per model variant.
ALTMAN_ZONES = {
    "original": {"safe": 2.99, "distress": 1.81},   # public manufacturers (Z)
    "private": {"safe": 2.90, "distress": 1.23},    # private firms (Z')
    "emerging": {"safe": 2.60, "distress": 1.10},   # non-mfg / emerging (Z'')
}

# Benford first-digit MAD conformity thresholds (Nigrini, 2012).
BENFORD_MAD_THRESHOLDS = {
    "close": 0.006,        # < 0.006  -> close conformity
    "acceptable": 0.012,   # < 0.012  -> acceptable conformity
    "marginal": 0.015,     # < 0.015  -> marginally acceptable; >= 0.015 nonconformity
}
BENFORD_MIN_SAMPLE = 50    # below this, results are not statistically meaningful

# Risk-rating bands used across the UI and report.
RISK_LEVELS = ("low", "medium", "high")

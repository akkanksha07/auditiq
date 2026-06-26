"""Extract text and tables from a PDF annual report using pdfplumber."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import pdfplumber

from ..config import settings

# Pages likely to hold the primary financial statements.
_STATEMENT_KEYWORDS = (
    "balance sheet", "statement of financial position", "income statement",
    "statement of profit", "statement of operations", "cash flow",
    "consolidated statement",
)


@dataclass
class PdfContent:
    full_text: str
    page_texts: list[str] = field(default_factory=list)
    tables: list[list] = field(default_factory=list)
    num_pages: int = 0

    @property
    def scanned_pages(self) -> int:
        """How many pages were actually read (<= num_pages, bounded by the page cap)."""
        return len(self.page_texts)

    @property
    def financial_text(self) -> str:
        """Text from statement pages (falls back to the whole document)."""
        hits = [t for t in self.page_texts if any(k in t.lower() for k in _STATEMENT_KEYWORDS)]
        return "\n".join(hits) if hits else self.full_text


def _read(pdf, max_pages: int) -> PdfContent:
    total = len(pdf.pages)
    page_texts: list[str] = []
    tables: list[list] = []
    for page in pdf.pages[:max_pages]:
        page_texts.append(page.extract_text() or "")
        tables.extend(page.extract_tables() or [])
    return PdfContent(
        full_text="\n".join(page_texts), page_texts=page_texts,
        tables=tables, num_pages=total,
    )


def read_pdf(path: Union[str, Path], max_pages: Optional[int] = None) -> PdfContent:
    with pdfplumber.open(str(path)) as pdf:
        return _read(pdf, max_pages or settings.max_pdf_pages)


def read_pdf_bytes(data: bytes, max_pages: Optional[int] = None) -> PdfContent:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return _read(pdf, max_pages or settings.max_pdf_pages)

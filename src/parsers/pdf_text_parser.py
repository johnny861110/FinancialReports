"""
PDF text extraction using pdfplumber.
Gracefully degrades when pdfplumber is not installed.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.info("pdfplumber not installed — PDF text extraction unavailable")


@dataclass
class PageText:
    """Text content extracted from a single PDF page."""

    page_number: int
    text: str
    char_count: int
    has_tables: bool


def extract_pages(pdf_path: Path) -> list[PageText]:
    """
    Extract text from all pages of a PDF.

    Returns a list of PageText objects ordered by page number.
    If pdfplumber is not installed, returns an empty list.
    """
    if not HAS_PDFPLUMBER:
        logger.warning("pdfplumber not available; cannot extract PDF text from %s", pdf_path)
        return []

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error("PDF file not found: %s", pdf_path)
        return []

    pages: list[PageText] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                    # Detect if page likely contains tables
                    has_tables = _has_table_indicators(text, page)
                    pages.append(
                        PageText(
                            page_number=i,
                            text=text,
                            char_count=len(text),
                            has_tables=has_tables,
                        )
                    )
                except Exception as exc:
                    logger.warning("Failed to extract page %d from %s: %s", i, pdf_path.name, exc)
                    pages.append(PageText(page_number=i, text="", char_count=0, has_tables=False))
    except Exception as exc:
        logger.error("Failed to open PDF %s: %s", pdf_path, exc)

    logger.info("Extracted %d pages from %s", len(pages), pdf_path.name)
    return pages


def _has_table_indicators(text: str, page) -> bool:
    """Heuristic: check for table presence using structural cues."""
    # Try pdfplumber's built-in table detection
    try:
        if page.find_tables():
            return True
    except Exception:
        pass

    # Text-based heuristics: multiple whitespace-separated columns, numeric patterns
    lines_with_numbers = sum(
        1 for line in text.splitlines() if re.search(r"\d{4,}", line) and len(line.split()) >= 3
    )
    return lines_with_numbers >= 5

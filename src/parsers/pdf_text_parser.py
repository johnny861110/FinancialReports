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
    from pdfplumber.utils.text import extract_text as _extract_text_from_chars

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.info("pdfplumber not installed — PDF text extraction unavailable")


# pdfminer decides a character is upright with `a * d * scaling > 0 and b * c <= 0`,
# an exact test on the font matrix. Taiwan filing PDFs routinely emit a matrix whose
# off-diagonal terms are a numerically negligible skew that happens to share a sign —
# e.g. b=-1.20e-07, c=-2.57e-08, whose product is +3.1e-15, so `b * c <= 0` is false.
# The character is then flagged rotated even though it sits on an ordinary horizontal
# baseline. pdfplumber lays rotated characters out as vertical text, so a normal table
# is emitted one character per line:
#
#     成
#     累
#     1
#
# That is the "character soup" that made a quarter of the chunk corpus unreadable and,
# because those chunks land in the high-scoring statement sections, outrank real prose.
# Restoring the flag for matrices that are axis-aligned to within this tolerance
# recovers the table as ordinary text. Genuinely rotated text (|b|, |c| near the scale
# of a and d) is left alone.
_MATRIX_SKEW_TOLERANCE = 1e-3


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
                    text = _extract_page_text(page)
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


def _deskew_upright_flags(chars: list[dict]) -> tuple[list[dict], int]:
    """
    Restore the `upright` flag on characters that pdfminer misflagged as rotated.

    See `_MATRIX_SKEW_TOLERANCE`. Returns the (possibly rewritten) character list and
    the number of characters corrected. Characters are copied rather than mutated so
    the page's own cache is left untouched.
    """
    corrected: list[dict] = []
    fixed = 0
    for char in chars:
        matrix = char.get("matrix")
        if not char.get("upright", True) and matrix and len(matrix) >= 4:
            a, b, c, d = matrix[0], matrix[1], matrix[2], matrix[3]
            scale = max(abs(a), abs(d))
            if (
                scale > 0
                and a * d > 0
                and abs(b) <= _MATRIX_SKEW_TOLERANCE * scale
                and abs(c) <= _MATRIX_SKEW_TOLERANCE * scale
            ):
                char = {**char, "upright": True}
                fixed += 1
        corrected.append(char)
    return corrected, fixed


def _extract_page_text(page) -> str:
    """
    Extract a page's text, first repairing characters that pdfminer misflagged as
    rotated. Falls back to pdfplumber's own extraction if nothing needed repair or
    if re-extraction fails, so behaviour is unchanged for well-formed pages.
    """
    try:
        chars, fixed = _deskew_upright_flags(page.chars)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Could not inspect chars on page %s: %s", page.page_number, exc)
        return page.extract_text() or ""

    if not fixed:
        return page.extract_text() or ""

    try:
        text = _extract_text_from_chars(chars) or ""
    except Exception as exc:
        logger.warning(
            "De-skewed extraction failed on page %s (%d chars); using default: %s",
            page.page_number,
            fixed,
            exc,
        )
        return page.extract_text() or ""

    logger.debug("Page %s: restored upright flag on %d chars", page.page_number, fixed)
    return text


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

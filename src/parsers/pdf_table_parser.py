"""
PDF financial table extraction — word-position based.

Uses pdfplumber word coordinates to reconstruct financial rows by grouping
words that share the same y-position, then identifies label and numeric value
columns by x-position.  This approach is more reliable than pdfplumber's
built-in `extract_tables()` for Taiwan financial report PDFs.

Used only when XBRL source is unavailable.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    logger.info("pdfplumber not installed — PDF table extraction unavailable")

# Match a number with optional sign, commas, and decimal (no $ prefix)
_NUMBER_RE = re.compile(r"^\(?\s*-?\s*[\d,]+(?:\.\d+)?\s*\)?$")
_CURRENCY_PREFIX = re.compile(r"^\$\s*")


def extract_financial_tables(
    pdf_path: Path,
    page_start: int,
    page_end: int,
) -> list[dict]:
    """
    Extract financial rows from a PDF page range using word-position grouping.

    Returns a list of row dicts:
      {page_number, label, value}

    Only used when XBRL source is unavailable.
    """
    if not HAS_PDFPLUMBER:
        logger.warning("pdfplumber not available; cannot extract tables from %s", pdf_path)
        return []

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error("PDF not found: %s", pdf_path)
        return []

    results: list[dict] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            total_pages = len(pdf.pages)
            start_idx = max(0, page_start - 1)
            end_idx = min(total_pages - 1, page_end - 1)

            for page_idx in range(start_idx, end_idx + 1):
                page = pdf.pages[page_idx]
                page_num = page_idx + 1
                try:
                    rows = _extract_rows_from_words(page, page_num)
                    results.extend(rows)
                except Exception as exc:
                    logger.warning(
                        "Word extraction failed on page %d of %s: %s",
                        page_num,
                        pdf_path.name,
                        exc,
                    )
    except Exception as exc:
        logger.error("Failed to open PDF %s: %s", pdf_path, exc)

    logger.info(
        "Extracted %d rows from pages %d-%d of %s",
        len(results),
        page_start,
        page_end,
        pdf_path.name,
    )
    return results


def _extract_rows_from_words(page, page_num: int) -> list[dict]:
    """
    Group words by y-position into rows, then for each row identify
    a text label and numeric value.
    """
    words = page.extract_words(x_tolerance=5, y_tolerance=3)
    if not words:
        return []

    # Group by rounded y-position (2px bucket)
    row_map: dict[int, list[dict]] = defaultdict(list)
    for w in words:
        y_key = round(w["top"] / 2) * 2
        row_map[y_key].append(w)

    rows: list[dict] = []
    for y_key in sorted(row_map.keys()):
        row_words = sorted(row_map[y_key], key=lambda w: w["x0"])
        result = _parse_row(row_words, page_num)
        if result:
            rows.append(result)
    return rows


def _parse_row(words: list[dict], page_num: int) -> dict | None:
    """
    From a sorted list of words on the same line, attempt to extract
    a (label, value) pair.

    Strategy:
    - Leftmost word(s) form the label (Chinese text or code)
    - Rightmost numeric token is the value for the current period
    - Skip percentage columns (values ≤ 100 that follow a large number)
    """
    if not words:
        return None

    texts = [w["text"] for w in words]
    # Find all numeric tokens (strip $ and parentheses which denote negatives)
    # Skip pure 4-digit tokens: they are Taiwan account codes (e.g. 4000, 5900)
    _ACCOUNT_CODE = re.compile(r"^\d{4}$")
    numeric_positions: list[tuple[int, float]] = []  # (word_index, value)
    for i, text in enumerate(texts):
        if _ACCOUNT_CODE.match(text):
            continue  # skip account codes like 4000, 5900
        clean = _CURRENCY_PREFIX.sub("", text).strip()
        # Handle parenthesized negatives: (1,234) → -1234
        is_neg = clean.startswith("(") and clean.endswith(")")
        clean_inner = clean.strip("()").strip()
        clean_no_comma = clean_inner.replace(",", "")
        if _NUMBER_RE.match(clean) and clean_no_comma:
            try:
                val = float(clean_no_comma)
                if is_neg:
                    val = -val
                numeric_positions.append((i, val))
            except ValueError:
                pass

    if not numeric_positions:
        return None

    # The first large-magnitude number is likely the financial figure
    # (percentage columns contain small numbers ≤ 100)
    financial_nums = [(i, v) for i, v in numeric_positions if abs(v) > 100]
    if not financial_nums:
        return None

    first_num_idx, value = financial_nums[0]

    # Label = all text tokens before the first numeric token
    label_parts = [texts[j] for j in range(first_num_idx) if not _is_pure_digit(texts[j])]
    # Remove account codes (pure 4-digit numbers at start)
    label_parts = [p for p in label_parts if not re.match(r"^\d{4}$", p)]
    # Remove note references like 六(一) or 六(三十一)及七
    label_parts = [p for p in label_parts if not re.match(r"^[一二三四五六七八九十]+[\(（]", p)]
    # Remove conjunction continuations from wrapped note references (e.g. "及七")
    label_parts = [p for p in label_parts if not re.match(r"^及[一二三四五六七八九十]+$", p)]
    label = "".join(label_parts).strip()

    if not label or len(label) < 2:
        return None
    # Skip rows whose label is entirely a note-continuation fragment
    if re.match(r"^[及及，、]+[一二三四五六七八九十\(\）\(\)]+$", label):
        return None

    return {
        "page_number": page_num,
        "label": label,
        "value": value,
    }


def _is_pure_digit(text: str) -> bool:
    return bool(re.match(r"^[\d,.\(\)\-\$\s]+$", text))


def tables_to_facts(tables: list[dict]) -> list[dict]:
    """
    Compatibility shim: the new extract_financial_tables() already returns
    {page_number, label, value} dicts — just pass them through.
    """
    return tables

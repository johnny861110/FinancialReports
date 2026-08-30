"""
PDF section detection and RAG chunk builder.
Splits document pages into labeled sections and then into overlapping chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.parsers.pdf_text_parser import PageText


def _stmt_pattern(title: str) -> str:
    """
    Build a regex that matches a financial-statement title header.
    Handles optional spaces between Chinese characters (common in PDF extraction)
    and requires a date marker (民國) within 300 chars to exclude TOC entries.
    """
    # Allow zero or more whitespace between each character
    spaced = r"[\s]*".join(title)
    return spaced + r"[\s\S]{0,300}民國"


SECTION_PATTERNS: dict[str, list[str]] = {
    "income_statement": [
        _stmt_pattern("合併綜合損益表"),
        _stmt_pattern("綜合損益表"),
        _stmt_pattern("合併損益及其他綜合損益表"),
    ],
    "balance_sheet": [
        _stmt_pattern("合併資產負債表"),
        _stmt_pattern("合併財務狀況表"),
        _stmt_pattern("資產負債表"),
        _stmt_pattern("財務狀況表"),
    ],
    "cash_flow": [
        _stmt_pattern("合併現金流量表"),
        _stmt_pattern("現金流量表"),
    ],
    "equity_statement": [
        _stmt_pattern("合併權益變動表"),
        _stmt_pattern("權益變動表"),
    ],
    "notes": [r"合併財務報表附註", r"財務報表附註"],
    "auditor": [r"獨立核數師報告", r"獨立審計師報告", r"會計師核閱報告", r"會計師查核報告"],
    "accounting_policy": [r"重大會計政策"],
    "eps_note": [r"每股盈餘"],
    "risk": [r"風險管理"],
}

# Supplementary schedules (附表) are their own thing: endorsements, securities
# held, related-party purchases and sales, loans to others. They carry no
# heading the statement patterns above recognise, so without this every one of
# them was absorbed by whatever section preceded it -- one filing had a
# 92-page "accounting_policy" section that was mostly schedules.
#
# Detection needs all three parts, measured over 7,875 pages:
#   * the marker alone fires on 1,317 pages, but 136 of those are body text
#     saying "請詳附表四" -- a cross-reference, not a schedule;
#   * requiring a schedule header (unit line or 民國 date) leaves 479 genuine
#     starts;
#   * the 702 marker pages without a header are continuations that do not
#     repeat it -- 75% fall within 12 pages of a start -- and correctly inherit
#     the section rather than beginning a new one.
_SCHEDULE_MARKER = re.compile(r"附表[一二三四五六七八九十]", re.MULTILINE)
_SCHEDULE_HEADER = re.compile(r"單位：新台幣|民國[0-9一二三四五六七八九十]+年", re.MULTILINE)
_SCHEDULE_CROSSREF = re.compile(r"[詳見參閱][^。]{0,6}附表", re.MULTILINE)


def _detect_schedule(text: str) -> tuple[str, str] | None:
    """Detect the first page of a supplementary schedule."""
    if not _SCHEDULE_MARKER.search(text):
        return None
    if _SCHEDULE_CROSSREF.search(text):
        return None
    if not _SCHEDULE_HEADER.search(text):
        return None
    match = _SCHEDULE_MARKER.search(text)
    return "schedule", match.group(0) if match else "附表"


# Pre-compiled patterns for speed (MULTILINE so \n works in patterns)
_COMPILED: dict[str, list[re.Pattern]] = {
    section: [re.compile(p, re.MULTILINE) for p in patterns]
    for section, patterns in SECTION_PATTERNS.items()
}

# A monetary figure in a Taiwan filing, which groups digits with commas. Matching on
# `\d{4,}` alone missed nearly all of them — `2,394,804,250` has no run of four digits —
# so `contains_numbers` and the table heuristic fired on about 5% of the corpus while a
# quarter of it was numeric table text.
_FINANCIAL_NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+|\d{4,}")

# Letters and CJK, i.e. word characters that are not digits or underscore.
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")


@dataclass
class DocumentSection:
    """A logical section of a financial report document."""

    section_type: str
    title: str
    page_start: int
    page_end: int
    content: str


def _detect_section(text: str) -> tuple[str, str] | None:
    """
    Detect if a page starts a new section.
    Returns (section_type, matched_title) or None.

    Only examines the first 800 characters of the page so that
    incidental keyword mentions deep inside body text don't trigger
    a false section boundary. Schedules are the exception: their marker
    averages character 982 on a page, because these are wide landscape
    tables whose extraction order puts the heading block late. They are
    matched over the whole page instead, and rely on the cross-reference
    exclusion rather than position to avoid false boundaries.
    """
    schedule = _detect_schedule(text)
    if schedule:
        return schedule

    search_window = text[:800]
    for section_type, patterns in _COMPILED.items():
        for pattern in patterns:
            m = pattern.search(search_window)
            if m:
                # Extract the matched line as the title
                start = max(0, m.start() - 5)
                end = min(len(search_window), m.end() + 40)
                title_candidate = search_window[start:end].splitlines()[0].strip()
                return section_type, title_candidate[:100]
    return None


def split_sections(pages: list[PageText]) -> list[DocumentSection]:
    """
    Detect and split sections from a list of page texts.
    Pages without a detected section belong to the previous section (or 'other').
    """
    if not pages:
        return []

    sections: list[DocumentSection] = []
    current_type = "other"
    current_title = "Document Start"
    current_start = pages[0].page_number
    current_content_parts: list[str] = []

    for page in pages:
        detection = _detect_section(page.text)
        if detection:
            # Save previous section
            if current_content_parts:
                sections.append(
                    DocumentSection(
                        section_type=current_type,
                        title=current_title,
                        page_start=current_start,
                        page_end=page.page_number - 1,
                        content="\n\n".join(current_content_parts),
                    )
                )
            current_type, current_title = detection
            current_start = page.page_number
            current_content_parts = [page.text]
        else:
            current_content_parts.append(page.text)

    # Flush last section
    if current_content_parts:
        last_page = pages[-1].page_number
        sections.append(
            DocumentSection(
                section_type=current_type,
                title=current_title,
                page_start=current_start,
                page_end=last_page,
                content="\n\n".join(current_content_parts),
            )
        )

    return sections


def build_chunks(
    sections: list[DocumentSection],
    chunk_size: int = 600,
    overlap: int = 50,
) -> list[dict]:
    """
    Build RAG-ready chunks from document sections.

    Rules:
    - Do not cross section boundaries
    - Target ~300-800 tokens; use char count as proxy (~2.5 chars/token for Chinese)
    - Each chunk carries page_start, page_end, section_type, section_title
    - Mark contains_numbers and contains_table

    Returns list of chunk dicts.
    """
    chunks: list[dict] = []
    for section_index, section in enumerate(sections):
        section_chunks = _chunk_text(
            section.content,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        for idx, (text_chunk, char_start, char_end) in enumerate(section_chunks):
            chunks.append(
                {
                    # Which section produced this chunk. Callers must attribute
                    # by this index: sections routinely share a
                    # (section_type, title) pair, so matching on those instead
                    # attributes one chunk to every section that shares the key.
                    "section_index": section_index,
                    "section_type": section.section_type,
                    "section_title": section.title,
                    "page_start": section.page_start,
                    "page_end": section.page_end,
                    "chunk_index": idx,
                    "content": text_chunk,
                    "char_offset_start": char_start,
                    "char_offset_end": char_end,
                    "contains_numbers": bool(_FINANCIAL_NUMBER.search(text_chunk)),
                    "contains_table": _looks_like_table(text_chunk),
                    "importance_score": _score_chunk(text_chunk, section.section_type),
                }
            )
    return chunks


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[str, int, int]]:
    """
    Split text into overlapping chunks.
    Returns list of (chunk_text, char_start, char_end).
    """
    if not text.strip():
        return []

    # Split on newlines first, then merge up to chunk_size
    results: list[tuple[str, int, int]] = []
    pos = 0
    length = len(text)

    while pos < length:
        end = min(pos + chunk_size, length)
        # Try to break at a newline near the end boundary
        if end < length:
            newline_pos = text.rfind("\n", pos, end)
            if newline_pos > pos + chunk_size // 2:
                end = newline_pos + 1
        chunk = text[pos:end]
        if chunk.strip():
            results.append((chunk, pos, end))
        # Advance with overlap
        pos = end - overlap if end - overlap > pos else end

    return results


def _looks_like_table(text: str) -> bool:
    """Heuristic: multiple lines with aligned whitespace and numbers."""
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    numeric_lines = sum(
        1 for line in lines if _FINANCIAL_NUMBER.search(line) and len(line.split()) >= 3
    )
    return numeric_lines >= 3


def _legibility(text: str) -> float:
    """
    How much of a chunk reads as language rather than table debris, in 0..1.

    Two independent ways a chunk turns into debris, both measured here:

    - `letter_ratio` — the share of non-space characters that are letters or CJK.
      A statement row such as `$ 2,394,804,250 $ 2,127,627,043` is nearly all
      digits, punctuation and currency marks.
    - `fragmentation` — the share of whitespace-separated tokens that are a single
      character. Shattered table text arrives as one character per token.

    The product punishes a chunk that is both number-dense and shattered hardest,
    while leaving ordinary prose that quotes a few figures essentially untouched.
    """
    compact = _WHITESPACE.sub("", text)
    if not compact:
        return 0.0
    letter_ratio = len(_LETTER.findall(compact)) / len(compact)
    tokens = text.split()
    fragmentation = (sum(1 for t in tokens if len(t) == 1) / len(tokens)) if tokens else 0.0
    return max(0.0, min(1.0, letter_ratio * (1.0 - fragmentation)))


# A chunk never falls below this fraction of its section's base score, so section
# ordering still decides between two equally legible chunks.
_LEGIBILITY_FLOOR = 0.4

_SECTION_BASE_SCORE = {
    "income_statement": 0.9,
    "balance_sheet": 0.9,
    "cash_flow": 0.85,
    "eps_note": 0.85,
    "revenue_note": 0.8,
    "notes": 0.6,
    "accounting_policy": 0.5,
    "auditor": 0.5,
    "equity_statement": 0.7,
    "risk": 0.6,
    "other": 0.4,
}


def _score_chunk(text: str, section_type: str) -> float:
    """
    Assign an importance score from the section type, scaled by how legible the
    chunk actually is.

    `importance_score` is the fallback ordering key for evidence retrieval: it decides
    which passages a filing returns when no embedding is available. Scoring on section
    type alone made that ranking prefer debris, because table-extraction wreckage
    concentrates in exactly the sections with the highest base score — a quarter of the
    corpus scored 0.70 against 0.65 for real prose.

    Rewarding digit density made this marginally worse and was removed. Measured on the
    19,152-chunk corpus it was close to inert in any case: the old `\\d{6,}` boost fired
    on 1.0% of debris chunks but 3.2% of prose, because Taiwan filings group digits with
    commas (`2,394,804,250` has no run of six digits), so it slightly favoured prose by
    accident while the section base did the real damage.
    """
    base = _SECTION_BASE_SCORE.get(section_type, 0.5)
    factor = _LEGIBILITY_FLOOR + (1.0 - _LEGIBILITY_FLOOR) * _legibility(text)
    return round(base * factor, 3)

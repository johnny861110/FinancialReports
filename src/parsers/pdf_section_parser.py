"""
PDF section detection and RAG chunk builder.
Splits document pages into labeled sections and then into overlapping chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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


# Taiwan filing notes are rigidly numbered, and that numbering is the only
# regular section boundary the document actually carries: 十、應收帳款,
# （四）財務風險管理目的與政策, 2.風險管理政策. Detecting it recovers ~950 distinct
# note headings across the corpus, against the nine hard-coded types below.
_NOTE_NUMBER = (
    r"(?:[（(][一二三四五六七八九十百]+[)）]"  # （四）
    r"|[一二三四五六七八九十百]{1,3}、"  # 十、
    r"|\d{1,2}[.、]"  # 12.
    r"|[A-Za-z][.、])"  # B.
)
_NOTE_HEADING = re.compile(rf"(?m)^[ \t]*{_NOTE_NUMBER}[ \t]*(\S[^\n]{{0,28}})$")

# These four patterns are bare substrings with no structural anchor, unlike the
# statement titles which require a 民國 date nearby. `風險管理` in particular
# matches ordinary prose -- "係依書面之風險管理政策", "風險管理部門依相關業務管理
# 部門" -- and financial-holding filings discuss risk management on nearly every
# notes page, so it fired 418 times across 67 filings and took 26.9% of all
# chunks. Requiring them to look like a heading is what stops that.
_UNANCHORED_SECTIONS = frozenset({"notes", "auditor", "accounting_policy", "eps_note", "risk"})

# A heading is terse, unpunctuated Chinese: not a cross-reference, not a
# table-of-contents row with a page range, not a table cell full of figures.
_HEADING_CROSSREF = re.compile(r"請?參閱|詳見|詳如|見附註")
_HEADING_TOC = re.compile(r"\d+\s*[~～-]\s*\d+\s*$|\.{4,}")
_HEADING_CJK = re.compile(r"[一-鿿]")
_HEADING_FIGURES = re.compile(r"\d[\d,]{2,}")
_MAX_HEADING_CHARS = 30


def _looks_like_heading(body: str) -> bool:
    """Whether a line's text (after any numbering) reads as a section heading."""
    body = body.strip()
    if not (2 <= len(body) <= _MAX_HEADING_CHARS):
        return False
    if body.endswith(("。", "，", "；")):
        return False
    if len(_HEADING_CJK.findall(body)) < 2:
        return False
    if "〃" in body or _HEADING_FIGURES.search(body):
        return False
    return not (_HEADING_CROSSREF.search(body) or _HEADING_TOC.search(body))


def _note_heading(text: str) -> str | None:
    """The first numbered note heading in a page's opening window, if any."""
    for match in _NOTE_HEADING.finditer(text[:800]):
        body = match.group(1).strip()
        if _looks_like_heading(body):
            return body
    return None


# Pre-compiled patterns for speed (MULTILINE so \n works in patterns)
_COMPILED: dict[str, list[re.Pattern]] = {
    section: [
        re.compile(rf"(?m)^[ \t]*(?:{_NOTE_NUMBER}[ \t]*)?{p}")
        if section in _UNANCHORED_SECTIONS
        else re.compile(p, re.MULTILINE)
        for p in patterns
    ]
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
    # Where each page begins and ends inside `content`, as (page_number, start,
    # end) with end exclusive. Sections concatenate their pages, so without this
    # a chunk's character offsets cannot be traced back to the page it came
    # from. Left empty by callers that build a section by hand; chunks then fall
    # back to the section's own span.
    page_spans: list[tuple[int, int, int]] = field(default_factory=list)


def _join_pages(pages: list[PageText]) -> tuple[str, list[tuple[int, int, int]]]:
    """Concatenate page texts, recording each page's range in the result."""
    separator = "\n\n"
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    offset = 0
    for index, page in enumerate(pages):
        if index:
            offset += len(separator)
        parts.append(page.text)
        spans.append((page.page_number, offset, offset + len(page.text)))
        offset += len(page.text)
    return separator.join(parts), spans


def _pages_for_range(
    spans: list[tuple[int, int, int]], start: int, end: int, fallback: tuple[int, int]
) -> tuple[int, int]:
    """The first and last page a half-open character range touches."""
    touched = [
        page for page, page_start, page_end in spans if page_start < end and start < page_end
    ]
    if not touched:
        # A range landing entirely in a separator touches no page; attribute it
        # to the last page that starts at or before it rather than to the whole
        # section.
        earlier = [page for page, page_start, _ in spans if page_start <= start]
        if earlier:
            return earlier[-1], earlier[-1]
        return fallback
    return touched[0], touched[-1]


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
                # The whole matched line is the title. The unanchored patterns
                # match at a line start, so slicing back from m.start() would
                # reach into the previous line instead.
                line_start = search_window.rfind("\n", 0, m.start()) + 1
                line_end = search_window.find("\n", m.start())
                line = search_window[
                    line_start : line_end if line_end != -1 else len(search_window)
                ].strip()
                if section_type in _UNANCHORED_SECTIONS:
                    body = re.sub(rf"^[ \t]*{_NOTE_NUMBER}[ \t]*", "", line)
                    if not _looks_like_heading(body):
                        continue
                return section_type, line[:100]
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
    current_pages: list[PageText] = []

    def flush(page_end: int) -> None:
        content, spans = _join_pages(current_pages)
        sections.append(
            DocumentSection(
                section_type=current_type,
                title=current_title,
                page_start=current_start,
                page_end=page_end,
                content=content,
                page_spans=spans,
            )
        )

    for page in pages:
        detection = _detect_section(page.text)
        if detection is None:
            # A numbered note heading is a section boundary in its own right,
            # and its text is a far better label than any of the nine types:
            # 無形資產, 所得稅, 營業收入, 不動產、廠房及設備. The type resets to the
            # generic "note" rather than inheriting, because a note about
            # 無形資產 sitting inside a stretch typed "risk" is not merely coarse,
            # it is wrong -- and anything trusting section_type is then misled.
            # A boring, true type beside a specific title beats a pretty lie.
            heading = _note_heading(page.text)
            if heading:
                detection = ("note", heading)

        if detection:
            # Save previous section
            if current_pages:
                flush(page.page_number - 1)
            current_type, current_title = detection
            current_start = page.page_number
            current_pages = [page]
        else:
            current_pages.append(page)

    # Flush last section
    if current_pages:
        flush(pages[-1].page_number)

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
            # A chunk covers a few hundred characters of a section that may run
            # for ninety pages. Copying the section's own page_start onto it --
            # which is what this did -- makes every citation in that section
            # point at its first page.
            page_start, page_end = _pages_for_range(
                section.page_spans,
                char_start,
                char_end,
                (section.page_start, section.page_end),
            )
            chunks.append(
                {
                    # Which section produced this chunk. Callers must attribute
                    # by this index: sections routinely share a
                    # (section_type, title) pair, so matching on those instead
                    # attributes one chunk to every section that shares the key.
                    "section_index": section_index,
                    "section_type": section.section_type,
                    "section_title": section.title,
                    "page_start": page_start,
                    "page_end": page_end,
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
    # A numbered note carries a real topic heading, so it is at least as useful
    # as the generic "notes" bucket it replaces.
    "note": 0.6,
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

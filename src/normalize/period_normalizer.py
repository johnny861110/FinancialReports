"""
Period / date normalization utilities.
Handles ROC ↔ CE year conversion and XBRL context period parsing.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from src.domain.identity import FilingIdentity
from src.domain.taxonomy import CANONICAL_CASHFLOW

logger = logging.getLogger(__name__)

# Quarter -> (start month-day, end month-day)
_QUARTER_DATES: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {
    "Q1": ((1, 1), (3, 31)),
    "Q2": ((1, 1), (6, 30)),  # Cumulative YTD in Taiwan
    "Q3": ((1, 1), (9, 30)),
    "Q4": ((1, 1), (12, 31)),
}

# First month of each quarter, for datasets that report the quarter on its own.
_QUARTER_START_MONTH: dict[str, int] = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}

# Boards whose companies file semiannually: no Q1 or Q3 report, so the Q2
# figures cover Jan-Jun rather than Apr-Jun. 7418 (興櫃) is the case on record --
# FinMind holds no 03-31 row for it and its 2026Q2 EPS equals the PDF's
# Jan-Jun column. companies.market is used rather than "no earlier filing in the
# DB", because the corpus is incomplete: most listed companies lack some quarter.
SEMIANNUAL_MARKETS = frozenset({"興櫃"})


def roc_to_ce(year: int) -> int:
    """Convert Republic of China year to Common Era (Gregorian) year."""
    return year + 1911


def ce_to_roc(year: int) -> int:
    """Convert Common Era year to Republic of China year."""
    return year - 1911


def parse_date_string(date_str: str) -> date | None:
    """
    Parse a date string in various formats to a date object.
    Handles: YYYY-MM-DD, YYYY/MM/DD, YYY/MM/DD (ROC).
    """
    if not date_str:
        return None
    date_str = date_str.strip()

    # Standard ISO format
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Slash format (CE)
    m = re.match(r"(\d{4})/(\d{2})/(\d{2})", date_str)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # ROC format: YYY/MM/DD (3 digit year)
    m = re.match(r"(\d{3})/(\d{2})/(\d{2})", date_str)
    if m:
        ce_year = roc_to_ce(int(m.group(1)))
        return date(ce_year, int(m.group(2)), int(m.group(3)))

    logger.debug("Cannot parse date string: '%s'", date_str)
    return None


def parse_period(context_element: Any) -> tuple[date | None, date | None, str]:
    """
    Parse an XBRL context element to extract period dates.

    Returns (period_start, period_end, period_type).
    period_type is 'instant' or 'duration'.
    """
    try:
        from lxml import etree

        for child in context_element.iter():
            local = etree.QName(child.tag).localname
            if local == "instant" and child.text:
                d = parse_date_string(child.text.strip())
                return d, d, "instant"

        start_date: date | None = None
        end_date: date | None = None
        for child in context_element.iter():
            local = etree.QName(child.tag).localname
            if local == "startDate" and child.text:
                start_date = parse_date_string(child.text.strip())
            elif local == "endDate" and child.text:
                end_date = parse_date_string(child.text.strip())

        if start_date or end_date:
            return start_date, end_date, "duration"
    except Exception as exc:
        logger.debug("period parse failed: %s", exc)

    return None, None, "duration"


def quarter_to_dates(identity: FilingIdentity) -> tuple[date, date]:
    """
    Return (period_start, period_end) for a quarter.
    Taiwan quarterly reports are cumulative YTD (Q2 = Jan–Jun, Q3 = Jan–Sep).
    """
    start_md, end_md = _QUARTER_DATES.get(identity.quarter, ((1, 1), (12, 31)))
    period_start = date(identity.year, start_md[0], start_md[1])
    period_end = date(identity.year, end_md[0], end_md[1])
    return period_start, period_end


def quarter_start(identity: FilingIdentity) -> date:
    """First day of the quarter itself (Q2 = Apr 1), unlike the YTD start above."""
    return date(identity.year, _QUARTER_START_MONTH.get(identity.quarter, 1), 1)


def finmind_period_start(identity: FilingIdentity, field: str, *, semiannual: bool = False) -> date:
    """
    Start of the period a FinMind duration value covers.

    The income statement dataset returns the quarter on its own (Q4 included:
    FinMind derives it as the year less Q1-Q3), so its start is the quarter's
    first day. The cash-flow dataset returns year-to-date, as Taiwanese cash-flow
    statements are filed, so its start is Jan 1. A semiannual filer's Q2 is
    Jan-Jun whichever dataset it came from.
    """
    if semiannual or field in CANONICAL_CASHFLOW:
        return date(identity.year, 1, 1)
    return quarter_start(identity)

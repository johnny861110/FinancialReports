"""When a held filing may still be a first version rather than the final one.

A filing is stale only if the statutory deadline for its quarter, plus a grace
period, has passed and the copy we hold was taken before that point. Data fetched
after the cutoff is never made stale by the passage of time alone, and a quarter
whose deadline has not passed is never stale.

Deadlines are the general-industry ones (Q1 5/15, Q2 8/14, Q3 11/14, Q4 3/31 of
the next year). Financial-sector issuers file on different dates; that
difference is deliberately not modelled here.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

DEFAULT_GRACE_DAYS = 14
GRACE_ENV = "FR_STALE_GRACE_DAYS"

# Deadlines are calendar dates in Taiwan; compare instants in that zone.
_TAIPEI = timezone(timedelta(hours=8))

# (month, day, years after the report year)
_DEADLINES = {
    "Q1": (5, 15, 0),
    "Q2": (8, 14, 0),
    "Q3": (11, 14, 0),
    "Q4": (3, 31, 1),
}


def grace_period() -> timedelta:
    """The configured grace period; a missing or invalid value uses the default."""
    try:
        days = float(os.environ[GRACE_ENV])
    except (KeyError, ValueError):
        days = DEFAULT_GRACE_DAYS
    return timedelta(days=max(days, 0))


def filing_deadline(year: int, quarter: str) -> date:
    """The statutory filing deadline for a quarter's report."""
    month, day, year_offset = _DEADLINES[quarter]
    return date(year + year_offset, month, day)


def stale_cutoff(year: int, quarter: str, grace: timedelta | None = None) -> datetime:
    """The instant after which a quarter's report is expected to be final.

    The end of the deadline day (Taiwan time) plus the grace period.
    """
    deadline = filing_deadline(year, quarter)
    end_of_deadline = datetime.combine(deadline + timedelta(days=1), datetime.min.time(), _TAIPEI)
    return end_of_deadline + (grace_period() if grace is None else grace)


def is_stale(
    year: int,
    quarter: str,
    updated_at: datetime,
    now: datetime,
    grace: timedelta | None = None,
) -> bool:
    """True when the cutoff has passed and the copy was taken before it."""
    cutoff = stale_cutoff(year, quarter, grace)
    return now > cutoff and updated_at < cutoff

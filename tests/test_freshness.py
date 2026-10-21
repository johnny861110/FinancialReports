"""Staleness is 'the held copy may predate the final report', not 'the copy is old'."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.api.freshness import (
    DEFAULT_GRACE_DAYS,
    GRACE_ENV,
    filing_deadline,
    grace_period,
    is_stale,
    stale_cutoff,
)

TAIPEI = timezone(timedelta(hours=8))
GRACE = timedelta(days=14)


def _at(y: int, m: int, d: int, h: int = 12) -> datetime:
    return datetime(y, m, d, h, tzinfo=TAIPEI)


@pytest.mark.parametrize(
    ("year", "quarter", "expected"),
    [
        (2025, "Q1", date(2025, 5, 15)),
        (2025, "Q2", date(2025, 8, 14)),
        (2025, "Q3", date(2025, 11, 14)),
        (2025, "Q4", date(2026, 3, 31)),  # the annual report is due the next year
    ],
)
def test_deadlines(year: int, quarter: str, expected: date) -> None:
    assert filing_deadline(year, quarter) == expected


def test_cutoff_is_end_of_deadline_day_plus_grace() -> None:
    assert stale_cutoff(2025, "Q1", GRACE) == datetime(2025, 5, 30, tzinfo=TAIPEI)


@pytest.mark.parametrize("quarter", ["Q1", "Q2", "Q3", "Q4"])
def test_quarter_not_yet_past_cutoff_is_never_stale(quarter: str) -> None:
    cutoff = stale_cutoff(2025, quarter, GRACE)
    assert not is_stale(2025, quarter, cutoff - timedelta(days=200), cutoff, GRACE)
    assert not is_stale(
        2025, quarter, cutoff - timedelta(days=200), cutoff - timedelta(days=1), GRACE
    )


@pytest.mark.parametrize("quarter", ["Q1", "Q2", "Q3", "Q4"])
def test_early_copy_goes_stale_after_cutoff(quarter: str) -> None:
    cutoff = stale_cutoff(2025, quarter, GRACE)
    taken = cutoff - timedelta(days=1)
    assert not is_stale(2025, quarter, taken, cutoff, GRACE)
    assert is_stale(2025, quarter, taken, cutoff + timedelta(seconds=1), GRACE)


@pytest.mark.parametrize("quarter", ["Q1", "Q2", "Q3", "Q4"])
def test_copy_taken_after_cutoff_never_goes_stale(quarter: str) -> None:
    cutoff = stale_cutoff(2025, quarter, GRACE)
    for taken in (cutoff, cutoff + timedelta(seconds=1)):
        assert not is_stale(2025, quarter, taken, cutoff + timedelta(days=3650), GRACE)


def test_q4_crosses_the_year_boundary() -> None:
    # 2025Q4 is not stale in December 2025 or in the first weeks of 2026, however
    # old the copy: its deadline is 2026-03-31.
    old_copy = _at(2025, 11, 1)
    assert not is_stale(2025, "Q4", old_copy, _at(2025, 12, 31), GRACE)
    assert not is_stale(2025, "Q4", old_copy, _at(2026, 4, 14), GRACE)
    assert is_stale(2025, "Q4", old_copy, _at(2026, 4, 16), GRACE)
    # A copy fetched once the grace period is over is final.
    assert not is_stale(2025, "Q4", _at(2026, 4, 16), _at(2027, 1, 1), GRACE)


def test_grace_boundary_is_exact() -> None:
    deadline_end = datetime(2025, 5, 16, tzinfo=TAIPEI)
    # With no grace, the cutoff is the end of the deadline day itself.
    assert stale_cutoff(2025, "Q1", timedelta(0)) == deadline_end
    assert is_stale(
        2025,
        "Q1",
        deadline_end - timedelta(hours=1),
        deadline_end + timedelta(minutes=1),
        timedelta(0),
    )
    # With grace, the same instants are still inside the window.
    assert not is_stale(
        2025, "Q1", deadline_end - timedelta(hours=1), deadline_end + timedelta(minutes=1), GRACE
    )


def test_utc_and_taipei_instants_compare_correctly() -> None:
    cutoff = stale_cutoff(2025, "Q1", GRACE)  # 2025-05-30 00:00 +08:00 == 05-29 16:00 UTC
    taken = datetime(2025, 5, 29, 15, 59, tzinfo=timezone.utc)
    assert is_stale(2025, "Q1", taken, datetime(2025, 5, 29, 16, 1, tzinfo=timezone.utc), GRACE)
    assert not is_stale(
        2025,
        "Q1",
        datetime(2025, 5, 29, 16, 0, tzinfo=timezone.utc),
        cutoff + timedelta(days=1),
        GRACE,
    )


def test_grace_defaults_and_env_override(monkeypatch) -> None:
    monkeypatch.delenv(GRACE_ENV, raising=False)
    assert grace_period() == timedelta(days=DEFAULT_GRACE_DAYS)
    monkeypatch.setenv(GRACE_ENV, "3")
    assert grace_period() == timedelta(days=3)
    monkeypatch.setenv(GRACE_ENV, "not-a-number")
    assert grace_period() == timedelta(days=DEFAULT_GRACE_DAYS)
    monkeypatch.setenv(GRACE_ENV, "-5")
    assert grace_period() == timedelta(0)

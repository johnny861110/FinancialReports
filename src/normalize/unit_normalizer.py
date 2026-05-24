"""
Financial unit normalization.
All monetary values are stored in TWD thousands.
"""

from __future__ import annotations

import logging

from src.domain.taxonomy import ALL_CANONICAL

logger = logging.getLogger(__name__)

MONETARY_CANONICAL = "TWD_thousands"

# Unit reference strings from XBRL -> multiplier to reach TWD thousands
_MONETARY_UNITS: dict[str, float] = {
    # Exact thousands already
    "twd": 0.001,  # raw TWD -> /1000
    "nt$": 0.001,
    "ntd": 0.001,
    "twd_thousands": 1.0,
    "twdthousands": 1.0,
    "thousands": 1.0,
    "千元": 1.0,
    # Millions
    "twd_millions": 1_000.0,
    "millions": 1_000.0,
    "百萬": 1_000.0,
    # Hundred millions (億)
    "twd_hundred_millions": 100_000.0,
    "億": 100_000.0,
}


def normalize_monetary(value: float, xbrl_unit: str) -> float:
    """
    Convert a monetary value to TWD_thousands.

    Handles: TWD, NT$, thousands, millions.
    If unit is unrecognised, assumes the value is already in thousands.
    """
    unit_key = xbrl_unit.lower().strip()
    multiplier = _MONETARY_UNITS.get(unit_key)
    if multiplier is None:
        # Default: assume already in thousands (most Taiwan XBRL reports)
        logger.debug("Unknown monetary unit '%s', assuming TWD_thousands", xbrl_unit)
        return value
    return value * multiplier


def normalize_per_share(value: float) -> float:
    """
    EPS value stays as-is (TWD per share).
    Validates range and returns the value unchanged if reasonable.
    """
    # Sanity check: EPS rarely exceeds 1000 or goes below -500 in Taiwan market
    if abs(value) > 10_000:
        logger.warning("Suspicious EPS value: %s — possible unit error", value)
    return value


def get_canonical_unit(field: str) -> str:
    """Return the canonical unit string for a given field name."""
    meta = ALL_CANONICAL.get(field, {})
    return meta.get("unit", MONETARY_CANONICAL)

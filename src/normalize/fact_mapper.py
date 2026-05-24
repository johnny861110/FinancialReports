"""
Map raw XBRL facts to canonical financial fields.
"""

from __future__ import annotations

import logging
from datetime import date

from src.domain.taxonomy import XBRL_TO_CANONICAL
from src.normalize.period_normalizer import parse_date_string
from src.normalize.unit_normalizer import (
    get_canonical_unit,
    normalize_monetary,
    normalize_per_share,
)

logger = logging.getLogger(__name__)

_PER_SHARE_FIELDS = {"eps_basic", "eps_diluted"}


def map_to_canonical(
    xbrl_tag: str,
    raw_value: float,
    unit_ref: str,
    period_info: dict,
) -> dict | None:
    """
    Map a single raw XBRL fact to canonical form.

    Steps:
    1. Look up xbrl_tag in XBRL_TO_CANONICAL
    2. Normalize unit
    3. Build canonical fact dict

    Returns None if tag is not mapped to any canonical field.
    """
    canonical_field = XBRL_TO_CANONICAL.get(xbrl_tag)
    if canonical_field is None:
        logger.debug("No canonical mapping for XBRL tag: %s", xbrl_tag)
        return None

    canonical_unit = get_canonical_unit(canonical_field)

    # Normalize value based on unit type
    if canonical_field in _PER_SHARE_FIELDS:
        normalized_value = normalize_per_share(raw_value)
    else:
        normalized_value = normalize_monetary(raw_value, unit_ref)

    # Parse period dates
    period_start: date | None = None
    period_end: date | None = None
    if isinstance(period_info.get("period_start"), str):
        period_start = parse_date_string(period_info["period_start"])
    elif isinstance(period_info.get("period_start"), date):
        period_start = period_info["period_start"]

    if isinstance(period_info.get("period_end"), str):
        period_end = parse_date_string(period_info["period_end"])
    elif isinstance(period_info.get("period_end"), date):
        period_end = period_info["period_end"]

    return {
        "field": canonical_field,
        "value": normalized_value,
        "unit": canonical_unit,
        "period_start": period_start,
        "period_end": period_end,
        "period_type": period_info.get("period_type", "duration"),
        "xbrl_tag": xbrl_tag,
        "source_type": "xbrl",
        "confidence": 1.0,
    }


def map_facts(raw_facts: list[dict]) -> list[dict]:
    """
    Map a list of raw XBRL fact dicts to canonical form.

    Deduplicates by field name, preferring the fact with the most complete period info.
    """
    canonical: dict[str, dict] = {}

    for raw in raw_facts:
        result = map_to_canonical(
            xbrl_tag=raw.get("xbrl_tag", ""),
            raw_value=raw.get("value", 0.0),
            unit_ref=raw.get("unit_ref", ""),
            period_info={
                "period_start": raw.get("period_start"),
                "period_end": raw.get("period_end"),
                "period_type": raw.get("period_type", "duration"),
            },
        )
        if result is None:
            continue

        field = result["field"]
        # Keep the fact with more complete date info
        if field not in canonical:
            canonical[field] = result
        else:
            existing = canonical[field]
            existing_score = (existing["period_start"] is not None) + (
                existing["period_end"] is not None
            )
            new_score = (result["period_start"] is not None) + (result["period_end"] is not None)
            if new_score > existing_score:
                canonical[field] = result

    return list(canonical.values())

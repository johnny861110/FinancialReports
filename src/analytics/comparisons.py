"""
Period-over-period comparison utilities.
"""

from __future__ import annotations

import logging

from src.domain.identity import FilingIdentity

logger = logging.getLogger(__name__)

_SIGNIFICANCE_THRESHOLDS = {
    "large": 10.0,  # >=10% change
    "moderate": 3.0,  # >=3% change
    "small": 0.0,  # anything else
}


def compute_changes(
    current: dict[str, float],
    prior: dict[str, float],
) -> list[dict]:
    """
    For each field present in both current and prior, compute:
      {field, current_value, prior_value, change_abs, change_pct, direction, significance}

    Returns a list of comparison dicts sorted by abs(change_pct) descending.
    """
    results: list[dict] = []

    common_fields = set(current.keys()) & set(prior.keys())
    for field in common_fields:
        cur_val = current[field]
        prior_val = prior[field]
        change_abs = cur_val - prior_val

        if prior_val != 0:
            change_pct = (change_abs / abs(prior_val)) * 100
        else:
            change_pct = None

        direction = "up" if change_abs > 0 else ("down" if change_abs < 0 else "flat")

        if change_pct is not None:
            abs_pct = abs(change_pct)
            if abs_pct >= _SIGNIFICANCE_THRESHOLDS["large"]:
                significance = "large"
            elif abs_pct >= _SIGNIFICANCE_THRESHOLDS["moderate"]:
                significance = "moderate"
            else:
                significance = "small"
        else:
            significance = "unknown"

        results.append(
            {
                "field": field,
                "current_value": cur_val,
                "prior_value": prior_val,
                "change_abs": change_abs,
                "change_pct": change_pct,
                "direction": direction,
                "significance": significance,
            }
        )

    # Sort by significance then by abs change_pct
    significance_order = {"large": 0, "moderate": 1, "small": 2, "unknown": 3}
    results.sort(
        key=lambda x: (
            significance_order.get(x["significance"], 3),
            -(abs(x["change_pct"]) if x["change_pct"] is not None else 0),
        )
    )
    return results


def get_prior_quarter(identity: FilingIdentity) -> FilingIdentity:
    """Return the FilingIdentity for the immediately preceding quarter."""
    quarter_order = ["Q1", "Q2", "Q3", "Q4"]
    idx = quarter_order.index(identity.quarter)
    if idx == 0:
        return FilingIdentity(
            stock_code=identity.stock_code,
            year=identity.year - 1,
            quarter="Q4",
        )
    return FilingIdentity(
        stock_code=identity.stock_code,
        year=identity.year,
        quarter=quarter_order[idx - 1],
    )


def get_prior_year(identity: FilingIdentity) -> FilingIdentity:
    """Return the FilingIdentity for the same quarter in the previous year."""
    return FilingIdentity(
        stock_code=identity.stock_code,
        year=identity.year - 1,
        quarter=identity.quarter,
    )

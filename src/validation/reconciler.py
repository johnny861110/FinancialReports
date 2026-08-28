"""
Cross-source reconciliation: compare XBRL vs PDF facts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.storage.store import FilingStore

logger = logging.getLogger(__name__)


def reconcile_fact(
    xbrl_value: float,
    pdf_value: float,
    tolerance: float = 0.02,
) -> dict:
    """
    Compare XBRL vs PDF extracted value for the same field.

    Returns:
      {match, discrepancy_pct, preferred_source, xbrl_value, pdf_value}
    """
    if xbrl_value == 0 and pdf_value == 0:
        return {
            "match": True,
            "discrepancy_pct": 0.0,
            "preferred_source": "xbrl",
            "xbrl_value": xbrl_value,
            "pdf_value": pdf_value,
        }

    denominator = max(abs(xbrl_value), abs(pdf_value))
    if denominator == 0:
        return {
            "match": True,
            "discrepancy_pct": 0.0,
            "preferred_source": "xbrl",
            "xbrl_value": xbrl_value,
            "pdf_value": pdf_value,
        }

    discrepancy_pct = abs(xbrl_value - pdf_value) / denominator
    match = discrepancy_pct <= tolerance

    # XBRL is preferred as it is structured and authoritative
    preferred_source = "xbrl"
    if not match:
        logger.warning(
            "Reconciliation mismatch: XBRL=%s vs PDF=%s (%.2f%% discrepancy)",
            xbrl_value,
            pdf_value,
            discrepancy_pct * 100,
        )

    return {
        "match": match,
        "discrepancy_pct": round(discrepancy_pct * 100, 3),
        "preferred_source": preferred_source,
        "xbrl_value": xbrl_value,
        "pdf_value": pdf_value,
    }


def reconcile_filing(store: FilingStore, filing_key: str) -> list[dict]:
    """
    Cross-check all facts with multiple sources for a filing.
    Returns list of reconciliation results for fields with multiple sources.
    """
    facts = store.get_facts(filing_key)

    # Group by field name -> {source_type: value}
    by_field: dict[str, dict[str, float]] = {}
    for fact in facts:
        field = fact["field"]
        source = fact["source_type"]
        if field not in by_field:
            by_field[field] = {}
        by_field[field][source] = fact["value"]

    results: list[dict] = []
    for field, sources in by_field.items():
        if "xbrl" in sources and ("pdf_table" in sources or "pdf_text" in sources):
            xbrl_val = sources["xbrl"]
            pdf_val = sources.get("pdf_table") or sources.get("pdf_text", 0.0)
            reconciliation = reconcile_fact(xbrl_val, pdf_val)
            results.append(
                {
                    "field": field,
                    **reconciliation,
                }
            )

    return results

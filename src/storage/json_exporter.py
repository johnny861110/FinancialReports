"""
Export filing data to JSON for external consumption or archiving.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.storage.sqlite_store import SQLiteStore


def export_filing(store: SQLiteStore, filing_key: str) -> dict:
    """
    Export all data for a filing as a structured dict.
    Returns: {filing_key, facts, metrics, comparisons, events, insight_cards}
    """
    facts = store.get_facts(filing_key)
    metrics = store.get_metrics(filing_key)
    comparisons = store.get_comparisons(filing_key)
    events = store.get_events(filing_key)
    insight_cards = store.get_insight_cards(filing_key)
    validation = store.get_validation_results(filing_key)
    status = store.get_filing_status(filing_key)

    return {
        "filing_key": filing_key,
        "status": status,
        "facts": facts,
        "metrics": metrics,
        "comparisons": {
            "yoy": [c for c in comparisons if c["compare_type"] == "yoy"],
            "qoq": [c for c in comparisons if c["compare_type"] == "qoq"],
        },
        "events": events,
        "insight_cards": insight_cards,
        "validation": validation,
    }


def export_to_file(store: SQLiteStore, filing_key: str, output_path: str | Path) -> None:
    """Export filing data to a JSON file."""
    data = export_filing(store, filing_key)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def export_legacy_format(store: SQLiteStore, filing_key: str) -> dict:
    """
    Export in the legacy v2 JSON schema for backward compatibility.
    Maps canonical fields back to the old structure used by legacy scripts.
    """
    facts_dict = store.get_facts_dict(filing_key)
    metrics = {m["metric_name"]: m["value"] for m in store.get_metrics(filing_key)}

    # Build legacy-compatible structure
    parts = filing_key.split("_")
    stock_code = parts[0] if parts else filing_key
    period = parts[1] if len(parts) > 1 else ""

    legacy = {
        "stock_code": stock_code,
        "period": period,
        "filing_key": filing_key,
        "financial_data": {
            "income_statement": {
                "net_revenue": facts_dict.get("net_revenue"),
                "gross_profit": facts_dict.get("gross_profit"),
                "operating_income": facts_dict.get("operating_income"),
                "net_income": facts_dict.get("net_income"),
                "eps_basic": facts_dict.get("eps_basic"),
                "eps_diluted": facts_dict.get("eps_diluted"),
            },
            "balance_sheet": {
                "total_assets": facts_dict.get("total_assets"),
                "total_liabilities": facts_dict.get("total_liabilities"),
                "equity": facts_dict.get("equity"),
                "cash_and_equivalents": facts_dict.get("cash_and_equivalents"),
            },
            "cash_flow": {
                "operating_cash_flow": facts_dict.get("operating_cash_flow"),
                "investing_cash_flow": facts_dict.get("investing_cash_flow"),
                "financing_cash_flow": facts_dict.get("financing_cash_flow"),
            },
        },
        "metrics": {
            "gross_margin": metrics.get("gross_margin"),
            "operating_margin": metrics.get("operating_margin"),
            "net_margin": metrics.get("net_margin"),
            "roe": metrics.get("roe"),
            "roa": metrics.get("roa"),
        },
    }
    return legacy

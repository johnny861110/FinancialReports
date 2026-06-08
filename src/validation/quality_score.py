"""
Data quality scoring for financial filings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.taxonomy import ALL_CANONICAL

if TYPE_CHECKING:
    from src.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)

# Key fields that must be present for a "complete" general filing
_KEY_FIELDS = [
    "net_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "eps_basic",
    "total_assets",
    "total_liabilities",
    "equity",
    "operating_cash_flow",
]

# Bank/financial-sector filings have a different structure
_KEY_FIELDS_BANK = [
    "net_revenue",
    "net_interest_income",
    "net_income",
    "eps_basic",
    "total_assets",
    "total_liabilities",
    "equity",
    "operating_cash_flow",
]

# Stock codes for Taiwan financial sector (banks, insurance, securities)
_BANK_STOCK_PREFIX = ("28",)

# Weight breakdown (must sum to 1.0)
_WEIGHT_SOURCE_COVERAGE = 0.40   # formerly XBRL-only; now counts any structured source
_WEIGHT_COMPLETENESS = 0.30
_WEIGHT_VALIDATION_PASS = 0.20
_WEIGHT_EVIDENCE = 0.10


def compute_quality_score(filing_key: str, store: SQLiteStore) -> float:
    """
    Compute a 0.0–1.0 data quality score for a filing.

    Breakdown:
      40% — XBRL source coverage of canonical fields
      30% — Completeness (non-null key fields)
      20% — Validation rule pass rate
      10% — Evidence records exist for facts

    Returns score between 0.0 and 1.0.
    """
    facts = store.get_facts(filing_key)
    if not facts:
        return 0.0

    # Detect filing type to select appropriate key fields
    stock_code = filing_key.split("_")[0]
    is_bank = stock_code.startswith(_BANK_STOCK_PREFIX)
    key_fields = _KEY_FIELDS_BANK if is_bank else _KEY_FIELDS

    # --- Source Coverage (40%) — counts any structured source (XBRL, iXBRL, FinMind) ---
    canonical_count = len(ALL_CANONICAL)
    covered_fields = {f["field"] for f in facts if f["source_type"] in ("xbrl", "ixbrl", "finmind")}
    source_score = len(covered_fields) / canonical_count if canonical_count > 0 else 0.0

    # --- Completeness (30%) ---
    all_fields = {f["field"] for f in facts}
    present_key_fields = sum(1 for kf in key_fields if kf in all_fields)
    completeness_score = present_key_fields / len(key_fields)

    # --- Validation pass rate (20%) ---
    validation = store.get_validation_results(filing_key)
    if validation:
        passed = sum(1 for v in validation if v["passed"])
        # Weight errors more heavily
        error_fails = sum(1 for v in validation if not v["passed"] and v["severity"] == "error")
        validation_score = max(0.0, passed / len(validation) - error_fails * 0.1)
    else:
        validation_score = 0.5  # No validation run yet → neutral

    # --- Evidence coverage (10%) ---
    filing_id = store.get_filing_id(filing_key)
    evidence_score = 0.0
    if filing_id is not None:
        with store.conn() as c:
            from sqlalchemy import text

            fact_ids_with_evidence = c.execute(
                text(
                    "SELECT COUNT(DISTINCT fe.fact_id)"
                    " FROM fact_evidence fe"
                    " JOIN financial_facts ff ON ff.id=fe.fact_id"
                    " WHERE ff.filing_id=:fid"
                ),
                {"fid": filing_id},
            ).fetchone()
            total_facts = c.execute(
                text("SELECT COUNT(*) FROM financial_facts WHERE filing_id=:fid"),
                {"fid": filing_id},
            ).fetchone()

        n_evidence = fact_ids_with_evidence[0] if fact_ids_with_evidence else 0
        n_total = total_facts[0] if total_facts else 0
        evidence_score = (n_evidence / n_total) if n_total > 0 else 0.0

    score = (
        source_score * _WEIGHT_SOURCE_COVERAGE
        + completeness_score * _WEIGHT_COMPLETENESS
        + validation_score * _WEIGHT_VALIDATION_PASS
        + evidence_score * _WEIGHT_EVIDENCE
    )

    final_score = round(min(1.0, max(0.0, score)), 4)
    logger.info(
        "Quality score for %s: %.4f (source=%.2f, completeness=%.2f, validation=%.2f, evidence=%.2f)",
        filing_key,
        final_score,
        source_score,
        completeness_score,
        validation_score,
        evidence_score,
    )
    return final_score

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

# Key fields that must be present for a "complete" filing
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

# Weight breakdown (must sum to 1.0)
_WEIGHT_XBRL_COVERAGE = 0.40
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

    # --- XBRL Coverage (40%) ---
    canonical_count = len(ALL_CANONICAL)
    xbrl_fields = {f["field"] for f in facts if f["source_type"] in ("xbrl", "ixbrl")}
    xbrl_score = len(xbrl_fields) / canonical_count if canonical_count > 0 else 0.0

    # --- Completeness (30%) ---
    all_fields = {f["field"] for f in facts}
    present_key_fields = sum(1 for kf in _KEY_FIELDS if kf in all_fields)
    completeness_score = present_key_fields / len(_KEY_FIELDS)

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
        xbrl_score * _WEIGHT_XBRL_COVERAGE
        + completeness_score * _WEIGHT_COMPLETENESS
        + validation_score * _WEIGHT_VALIDATION_PASS
        + evidence_score * _WEIGHT_EVIDENCE
    )

    final_score = round(min(1.0, max(0.0, score)), 4)
    logger.info(
        "Quality score for %s: %.4f (xbrl=%.2f, completeness=%.2f, validation=%.2f, evidence=%.2f)",
        filing_key,
        final_score,
        xbrl_score,
        completeness_score,
        validation_score,
        evidence_score,
    )
    return final_score

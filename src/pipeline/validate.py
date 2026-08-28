"""
Pipeline stage 3: Validate — run quality checks and compute quality score.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.identity import FilingIdentity

if TYPE_CHECKING:
    from src.storage.store import FilingStore

logger = logging.getLogger(__name__)


def run_validate(identity: FilingIdentity, store: FilingStore) -> dict:
    """
    Pipeline stage 3: Run validation rules and compute quality score.

    Steps:
    1. Load facts dict
    2. run_all_rules(facts) → save validation_results
    3. reconcile_filing if multiple sources
    4. compute_quality_score → update filing
    5. Update filing status to "validated"

    Returns {"score", "passed", "failed", "warnings"}
    """
    fk = identity.filing_key
    store.log_pipeline_run(fk, "validate", "started")

    try:
        current_status = store.get_filing_status(fk)
        if current_status == "validated":
            logger.info("Skipping validate for %s — already validated", fk)
            store.log_pipeline_run(fk, "validate", "skipped")
            return {"score": None, "passed": 0, "failed": 0, "warnings": 0, "status": "skipped"}

        filing_id = store.get_filing_id(fk)
        if filing_id is None:
            raise ValueError(f"Filing not found: {fk}")

        # 1. Load facts
        facts_dict = store.get_facts_dict(fk)

        # 2. Run validation rules
        from src.validation.rules import run_all_rules

        rule_results = run_all_rules(facts_dict)
        for res in rule_results:
            store.save_validation_result(
                filing_id,
                rule_name=res["rule_id"],
                passed=bool(res["passed"]),
                severity=res["severity"],
                message=res["message"],
            )

        n_passed = sum(1 for r in rule_results if r["passed"])
        n_failed = sum(1 for r in rule_results if not r["passed"] and r["severity"] == "error")
        n_warnings = sum(1 for r in rule_results if not r["passed"] and r["severity"] == "warning")

        logger.info(
            "Validation for %s: %d passed, %d errors, %d warnings",
            fk,
            n_passed,
            n_failed,
            n_warnings,
        )

        # 3. Reconcile multiple sources
        from src.validation.reconciler import reconcile_filing

        reconciliation = reconcile_filing(store, fk)
        if reconciliation:
            mismatches = [r for r in reconciliation if not r["match"]]
            if mismatches:
                logger.warning("%d source reconciliation mismatches for %s", len(mismatches), fk)

        # 4. Quality score
        from src.validation.quality_score import compute_quality_score

        score = compute_quality_score(fk, store)

        # Save quality score to filing
        with store.conn() as c:
            from sqlalchemy import text

            c.execute(
                text("UPDATE filings SET quality_score=:s WHERE id=:id"),
                {"s": score, "id": filing_id},
            )

        # 5. Update status
        store.update_filing_status(filing_id, "validated")
        store.log_pipeline_run(fk, "validate", "completed")

        return {
            "score": score,
            "passed": n_passed,
            "failed": n_failed,
            "warnings": n_warnings,
            "status": "completed",
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Validate failed for %s: %s", fk, exc, exc_info=True)
        store.log_pipeline_run(fk, "validate", "failed", error=error_msg)
        raise

"""
Pipeline stage 4: Build Insights — compute metrics, comparisons, events, and insight cards.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.analytics.comparisons import compute_changes, get_prior_quarter, get_prior_year
from src.analytics.event_detector import detect_events
from src.analytics.insight_builder import build_all_insights
from src.analytics.metrics import compute_all_metrics
from src.domain.identity import FilingIdentity
from src.domain.models import InsightCard

if TYPE_CHECKING:
    from src.storage.store import FilingStore

logger = logging.getLogger(__name__)


def run_build_insights(identity: FilingIdentity, store: FilingStore) -> dict:
    """
    Pipeline stage 4: Compute analytics and build insight cards.

    Steps:
    1. Load facts dict
    2. compute_all_metrics(facts) → save financial_metrics
    3. Load prior period facts → compute_changes (yoy + qoq) → save period_comparisons
    4. detect_events → save detected_events
    5. build_all_insights → save insight_cards
    6. Update filing status to "insight_ready"

    Returns {"metrics_count", "insights_count", "events_count"}
    """
    fk = identity.filing_key
    store.log_pipeline_run(fk, "insights", "started")

    try:
        filing_id = store.get_filing_id(fk)
        if filing_id is None:
            raise ValueError(f"Filing not found: {fk}")

        # A filing with no source document has nothing behind its numbers, and
        # must not present as ready. Before the ingest guard existed, all three
        # downloads returning None still advanced the filing, and insights then
        # built cards from the FinMind fact fallback alone -- 2330_2026Q2
        # reported a 0.8176 quality score with no document and no retrievable
        # text. The ingest guard stops that happening again, but it cannot
        # demote filings the old code already advanced, so the invariant is
        # enforced here as well: checked before the already-ready short-circuit
        # so an existing violation is corrected rather than skipped over.
        if not store.count_source_docs(filing_id):
            if current_status_is_ready := store.get_filing_status(fk) == "insight_ready":
                store.update_filing_status(filing_id, "extracted")
            store.log_pipeline_run(fk, "insights", "failed", error="filing has no source document")
            raise ValueError(
                f"{fk} has no source document; refusing to mark it insight_ready"
                + (" (demoted from insight_ready)" if current_status_is_ready else "")
            )

        current_status = store.get_filing_status(fk)
        if current_status == "insight_ready":
            logger.info("Skipping insights for %s — already insight_ready", fk)
            store.log_pipeline_run(fk, "insights", "skipped")
            return {"metrics_count": 0, "insights_count": 0, "events_count": 0, "status": "skipped"}

        # 1. Load facts
        facts = store.get_facts_dict(fk)

        # 2. Compute metrics
        metrics = compute_all_metrics(facts)
        for metric_name, value in metrics.items():
            store.save_metric(filing_id, metric_name, value)
        logger.info("Computed %d metrics for %s", len(metrics), fk)

        # 3. Period comparisons
        yoy_changes: list[dict] = []
        qoq_changes: list[dict] = []

        yoy_identity = get_prior_year(identity)
        yoy_facts = store.get_facts_dict(yoy_identity.filing_key)
        if yoy_facts:
            yoy_changes = compute_changes(facts, yoy_facts)
            yoy_filing_id = store.get_filing_id(yoy_identity.filing_key)
            for change in yoy_changes:
                store.save_comparison(
                    filing_id=filing_id,
                    compare_filing_id=yoy_filing_id,
                    field=change["field"],
                    compare_type="yoy",
                    current=change["current_value"],
                    prior=change["prior_value"],
                )
            logger.info("Computed %d YoY comparisons for %s", len(yoy_changes), fk)
        else:
            logger.info("No YoY prior data for %s (%s)", fk, yoy_identity.filing_key)

        qoq_identity = get_prior_quarter(identity)
        qoq_facts = store.get_facts_dict(qoq_identity.filing_key)
        if qoq_facts:
            qoq_changes = compute_changes(facts, qoq_facts)
            qoq_filing_id = store.get_filing_id(qoq_identity.filing_key)
            for change in qoq_changes:
                store.save_comparison(
                    filing_id=filing_id,
                    compare_filing_id=qoq_filing_id,
                    field=change["field"],
                    compare_type="qoq",
                    current=change["current_value"],
                    prior=change["prior_value"],
                )
            logger.info("Computed %d QoQ comparisons for %s", len(qoq_changes), fk)
        else:
            logger.info("No QoQ prior data for %s (%s)", fk, qoq_identity.filing_key)

        # 4. Detect events
        events = detect_events(facts, metrics, yoy_changes, qoq_changes)
        for event in events:
            store.save_event(
                filing_id=filing_id,
                event_type=event["event_type"],
                severity=event["severity"],
                title=event["title"],
                description=event["description"],
                related_fields=event.get("related_fields", []),
                confidence=event.get("confidence", 0.85),
            )
        logger.info("Detected %d events for %s", len(events), fk)

        # 5. Build insight cards
        insight_dicts = build_all_insights(
            identity=identity,
            facts=facts,
            metrics=metrics,
            yoy_changes=yoy_changes,
            qoq_changes=qoq_changes,
            events=events,
        )
        for card_dict in insight_dicts:
            card = InsightCard(
                filing_key=fk,
                card_type=card_dict["card_type"],
                title=card_dict["title"],
                summary=card_dict["summary"],
                data_points=card_dict.get("data_points", {}),
                sentiment=card_dict.get("sentiment"),
                confidence=card_dict.get("confidence", 0.8),
            )
            store.save_insight_card(filing_id, card)
        logger.info("Built %d insight cards for %s", len(insight_dicts), fk)

        # 6. Update status
        store.update_filing_status(filing_id, "insight_ready")
        store.log_pipeline_run(fk, "insights", "completed")

        return {
            "metrics_count": len(metrics),
            "insights_count": len(insight_dicts),
            "events_count": len(events),
            "status": "completed",
        }

    except Exception as exc:
        error_msg = str(exc)
        logger.error("Build insights failed for %s: %s", fk, exc, exc_info=True)
        store.log_pipeline_run(fk, "insights", "failed", error=error_msg)
        raise

"""
Context pack builder for LLM / agent consumption.
Assembles all relevant data about a filing into a single structured dict.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.agent.query_service import FinancialQueryService
from src.validation.quality_score import compute_quality_score

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def build_context_pack(
    service: FinancialQueryService,
    stock_code: str,
    year: int,
    quarter: str,
    question: str | None = None,
) -> dict:
    """
    Assemble a full evidence pack for agent / LLM use.

    Returns:
    {
        "filing": {filing_key, stock_code, year, quarter, status},
        "facts": [...],                 # all facts with metadata
        "metrics": {...},               # metric_name -> value
        "comparisons": {"yoy": [...], "qoq": [...]},
        "events": [...],
        "insight_cards": [...],
        "evidence_chunks": [...],       # text chunks relevant to question
        "quality_score": float,
    }
    """
    from src.domain.identity import FilingIdentity

    identity = FilingIdentity(stock_code=stock_code, year=year, quarter=quarter)
    fk = identity.filing_key

    # Filing metadata
    status = service.store.get_filing_status(fk)
    filing_meta = {
        "filing_key": fk,
        "stock_code": stock_code,
        "year": year,
        "quarter": quarter,
        "status": status,
    }

    # Facts
    facts = service.store.get_facts(fk)
    facts_dict = service.store.get_facts_dict(fk)

    # Metrics (flat dict)
    raw_metrics = service.store.get_metrics(fk)
    metrics = {m["metric_name"]: m["value"] for m in raw_metrics}

    # Comparisons
    yoy = service.store.get_comparisons(fk, compare_type="yoy")
    qoq = service.store.get_comparisons(fk, compare_type="qoq")

    # Events
    events = service.store.get_events(fk)

    # Insight cards
    insight_cards = service.store.get_insight_cards(fk)

    # Text evidence chunks
    evidence_chunks: list[dict] = []
    if question:
        from src.agent.retriever import ChunkRetriever

        retriever = ChunkRetriever(service.store)
        evidence_chunks = retriever.search_keyword(question, fk, limit=10)
    else:
        # Return top chunks by importance if no question
        all_chunks = service.store.get_chunks(fk)
        evidence_chunks = sorted(
            all_chunks,
            key=lambda x: x.get("importance_score", 0),
            reverse=True,
        )[:10]

    # Quality score
    try:
        quality_score = compute_quality_score(fk, service.store)
    except Exception as exc:
        logger.warning("Quality score computation failed: %s", exc)
        quality_score = 0.0

    return {
        "filing": filing_meta,
        "facts": facts,
        "facts_dict": facts_dict,
        "metrics": metrics,
        "comparisons": {"yoy": yoy, "qoq": qoq},
        "events": events,
        "insight_cards": insight_cards,
        "evidence_chunks": evidence_chunks,
        "quality_score": quality_score,
    }

"""
High-level query service for the financial agent.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.agent.retriever import ChunkRetriever, FactRetriever
from src.domain.identity import FilingIdentity

if TYPE_CHECKING:
    from src.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class FinancialQueryService:
    """
    Unified query interface for agent consumption.
    Combines structured facts, metrics, comparisons, and text retrieval.
    """

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self._facts = FactRetriever(store)
        self._chunks = ChunkRetriever(store)

    def _make_identity(self, stock_code: str, year: int, quarter: str) -> FilingIdentity:
        return FilingIdentity(stock_code=stock_code, year=year, quarter=quarter)

    def query_facts(
        self,
        stock_code: str,
        year: int,
        quarter: str,
        fields: list[str] | None = None,
    ) -> dict:
        """Return structured facts with metadata."""
        identity = self._make_identity(stock_code, year, quarter)
        facts = self._facts.get_facts(identity.filing_key, fields=fields)
        facts_dict = self._facts.get_facts_dict(identity.filing_key)
        return {
            "filing_key": identity.filing_key,
            "facts": facts,
            "facts_dict": facts_dict,
            "count": len(facts),
        }

    def query_insights(self, stock_code: str, year: int, quarter: str) -> list[dict]:
        """Return all insight cards for a filing."""
        identity = self._make_identity(stock_code, year, quarter)
        return self.store.get_insight_cards(identity.filing_key)

    def query_text(
        self,
        question: str,
        stock_code: str,
        year: int,
        quarter: str,
        limit: int = 10,
    ) -> list[dict]:
        """Return relevant text chunks using keyword search."""
        identity = self._make_identity(stock_code, year, quarter)
        # Extract key terms from question for multi-term search
        terms = [t for t in question.split() if len(t) > 1]
        results: list[dict] = []
        seen_ids: set[int] = set()

        for term in terms[:5]:  # Cap at 5 terms
            chunks = self._chunks.search_keyword(term, identity.filing_key, limit=limit)
            for chunk in chunks:
                if chunk["id"] not in seen_ids:
                    seen_ids.add(chunk["id"])
                    results.append(chunk)

        # Sort by importance score
        results.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        return results[:limit]

    def compare(
        self,
        stock_code: str,
        year: int,
        quarter: str,
        compare_type: str = "yoy",
    ) -> dict:
        """Return YoY or QoQ comparison data."""
        identity = self._make_identity(stock_code, year, quarter)
        comparisons = self._facts.get_comparisons(identity.filing_key, compare_type=compare_type)
        return {
            "filing_key": identity.filing_key,
            "compare_type": compare_type,
            "comparisons": comparisons,
            "count": len(comparisons),
        }

    def get_snapshot(self, stock_code: str, year: int, quarter: str) -> dict:
        """
        Return a compact snapshot of key facts, metrics, and status.
        Designed for quick LLM context injection.
        """
        identity = self._make_identity(stock_code, year, quarter)
        fk = identity.filing_key

        facts_dict = self._facts.get_facts_dict(fk)
        metrics = {m["metric_name"]: m["value"] for m in self._facts.get_metrics(fk)}
        status = self.store.get_filing_status(fk)
        events = self._facts.get_events(fk)
        cards = self.store.get_insight_cards(fk)

        return {
            "filing_key": fk,
            "stock_code": stock_code,
            "year": year,
            "quarter": quarter,
            "status": status,
            "key_facts": {
                "net_revenue": facts_dict.get("net_revenue"),
                "net_income": facts_dict.get("net_income"),
                "eps_basic": facts_dict.get("eps_basic"),
                "total_assets": facts_dict.get("total_assets"),
                "equity": facts_dict.get("equity"),
                "operating_cash_flow": facts_dict.get("operating_cash_flow"),
            },
            "key_metrics": {
                "gross_margin": metrics.get("gross_margin"),
                "operating_margin": metrics.get("operating_margin"),
                "net_margin": metrics.get("net_margin"),
                "roe": metrics.get("roe"),
                "current_ratio": metrics.get("current_ratio"),
                "free_cash_flow": metrics.get("free_cash_flow"),
            },
            "events": events[:5],
            "insight_cards_count": len(cards),
        }

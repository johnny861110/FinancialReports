"""
Data retrieval classes for the agent layer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.storage.store import FilingStore

logger = logging.getLogger(__name__)


class FactRetriever:
    """Retrieve structured financial facts and metrics from storage."""

    def __init__(self, store: FilingStore) -> None:
        self.store = store

    def get_facts(self, filing_key: str, fields: list[str] | None = None) -> list[dict]:
        """Return list of fact dicts, optionally filtered by field names."""
        return self.store.get_facts(filing_key, fields=fields)

    def get_facts_dict(self, filing_key: str) -> dict[str, float]:
        """Return {field: value} dict preferring XBRL source."""
        return self.store.get_facts_dict(filing_key)

    def get_metrics(self, filing_key: str) -> list[dict]:
        """Return computed financial metrics for a filing."""
        return self.store.get_metrics(filing_key)

    def get_comparisons(
        self,
        filing_key: str,
        compare_type: str | None = None,
    ) -> list[dict]:
        """Return period comparisons, optionally filtered by type (yoy|qoq)."""
        return self.store.get_comparisons(filing_key, compare_type=compare_type)

    def get_events(self, filing_key: str) -> list[dict]:
        """Return detected events for a filing."""
        return self.store.get_events(filing_key)

    def get_validation_results(self, filing_key: str) -> list[dict]:
        """Return validation results for a filing."""
        return self.store.get_validation_results(filing_key)


class ChunkRetriever:
    """Retrieve text chunks for RAG retrieval."""

    def __init__(self, store: FilingStore) -> None:
        self.store = store

    def search_keyword(
        self,
        query: str,
        filing_key: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        LIKE-based keyword search over chunk content.
        Returns up to `limit` matching chunks ordered by importance_score desc.
        """
        from sqlalchemy import text

        query_lower = f"%{query}%"
        with self.store.conn() as c:
            rows = c.execute(
                text(
                    "SELECT dc.id, dc.content, dc.page_number, dc.chunk_index,"
                    " ds.section_type, ds.title, dc.importance_score"
                    " FROM document_chunks dc"
                    " LEFT JOIN document_sections ds ON ds.id=dc.section_id"
                    " JOIN source_documents sd ON sd.id=dc.doc_id"
                    " JOIN filings fl ON fl.id=sd.filing_id"
                    " WHERE fl.filing_key=:fk"
                    "   AND dc.content LIKE :q"
                    " ORDER BY dc.importance_score DESC"
                    " LIMIT :lim"
                ),
                {"fk": filing_key, "q": query_lower, "lim": limit},
            ).fetchall()

        columns = [
            "id",
            "content",
            "page_number",
            "chunk_index",
            "section_type",
            "section_title",
            "importance_score",
        ]
        return [dict(zip(columns, row)) for row in rows]

    def get_by_section(self, filing_key: str, section_type: str) -> list[dict]:
        """Return all chunks for a specific section type."""
        return self.store.get_chunks(filing_key, section_type=section_type)

    def get_all_chunks(self, filing_key: str) -> list[dict]:
        """Return all chunks for a filing."""
        return self.store.get_chunks(filing_key)

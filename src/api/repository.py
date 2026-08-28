"""Read-only SQLite adapter for the v1 transport layer."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from src.storage.store import FilingStore


def _dicts(rows: Sequence[Any]) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in rows]


class APIRepository:
    def __init__(self, store: FilingStore) -> None:
        self.store = store

    def ready(self) -> bool:
        with self.store.conn() as conn:
            return conn.execute(text("SELECT 1")).scalar_one() == 1

    def list_stocks(
        self, limit: int, offset: int, query: str | None, industry: str | None
    ) -> tuple[list[dict[str, Any]], int]:
        where: list[str] = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if query:
            where.append(
                "(c.stock_code LIKE :query OR c.name_zh LIKE :query OR c.name_en LIKE :query)"
            )
            params["query"] = f"%{query}%"
        if industry:
            where.append("c.industry = :industry")
            params["industry"] = industry
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        with self.store.conn() as conn:
            total = conn.execute(
                text(f"SELECT COUNT(*) FROM companies c{clause}"), params
            ).scalar_one()
            rows = conn.execute(
                text(
                    "SELECT c.stock_code, c.name_zh, c.name_en, c.industry, c.market,"
                    " COUNT(f.id) AS periods_count FROM companies c"
                    " LEFT JOIN filings f ON f.company_id=c.id"
                    f"{clause} GROUP BY c.id ORDER BY c.stock_code LIMIT :limit OFFSET :offset"
                ),
                params,
            ).fetchall()
        return _dicts(rows), total

    def list_periods(
        self, stock_code: str, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        params = {"stock_code": stock_code, "limit": limit, "offset": offset}
        with self.store.conn() as conn:
            company_exists = conn.execute(
                text("SELECT 1 FROM companies WHERE stock_code=:stock_code"), params
            ).fetchone()
            if not company_exists:
                raise LookupError(stock_code)
            total = conn.execute(
                text(
                    "SELECT COUNT(*) FROM filings f JOIN companies c ON c.id=f.company_id"
                    " WHERE c.stock_code=:stock_code"
                ),
                params,
            ).scalar_one()
            rows = conn.execute(
                text(
                    "SELECT to_char(f.year, 'FM0000') || f.quarter AS period, f.status,"
                    " f.quality_score, f.updated_at FROM filings f"
                    " JOIN companies c ON c.id=f.company_id"
                    " WHERE c.stock_code=:stock_code"
                    " ORDER BY f.year DESC, CAST(SUBSTR(f.quarter, 2) AS INTEGER) DESC"
                    " LIMIT :limit OFFSET :offset"
                ),
                params,
            ).fetchall()
        return _dicts(rows), total

    def get_filing(self, stock_code: str, period: str) -> dict[str, Any] | None:
        filing_key = f"{stock_code}_{period}"
        with self.store.conn() as conn:
            filing = conn.execute(
                text(
                    "SELECT f.id, f.filing_key, f.year, f.quarter, f.status, f.quality_score,"
                    " f.created_at, f.updated_at, c.stock_code, c.name_zh, c.name_en,"
                    " c.industry, c.market FROM filings f"
                    " JOIN companies c ON c.id=f.company_id WHERE f.filing_key=:filing_key"
                ),
                {"filing_key": filing_key},
            ).fetchone()
            if filing is None:
                return None
            filing_data = dict(filing._mapping)
            filing_id = filing_data["id"]
            facts = _dicts(
                conn.execute(
                    text(
                        "SELECT id, field, value, unit, period_start, period_end, period_type,"
                        " source_type, confidence, xbrl_tag FROM financial_facts"
                        " WHERE filing_id=:id ORDER BY field, source_type"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            evidence = _dicts(
                conn.execute(
                    text(
                        "SELECT fe.fact_id, ff.field, fe.doc_id AS source_document_id,"
                        " fe.doc_id, fe.page_number, fe.section_title, fe.raw_text,"
                        " fe.raw_text AS excerpt, ff.confidence, ff.source_type,"
                        " fe.extraction_method, sd.url AS source_url, sd.checksum"
                        " FROM fact_evidence fe JOIN financial_facts ff ON ff.id=fe.fact_id"
                        " LEFT JOIN source_documents sd ON sd.id=fe.doc_id"
                        " WHERE ff.filing_id=:id ORDER BY fe.fact_id, fe.id"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            metrics = _dicts(
                conn.execute(
                    text(
                        "SELECT metric_name AS name, value, formula, inputs_json, confidence"
                        " FROM financial_metrics WHERE filing_id=:id ORDER BY metric_name"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            comparisons = _dicts(
                conn.execute(
                    text(
                        "SELECT pc.field, pc.compare_type, to_char(cf.year, 'FM0000') || cf.quarter"
                        " AS compare_period, pc.current_value, pc.prior_value, pc.change_abs,"
                        " pc.change_pct, pc.direction, pc.significance, pc.interpretation"
                        " FROM period_comparisons pc LEFT JOIN filings cf"
                        " ON cf.id=pc.compare_filing_id WHERE pc.filing_id=:id"
                        " ORDER BY pc.compare_type, pc.field"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            events = _dicts(
                conn.execute(
                    text(
                        "SELECT event_type, severity, title, description, related_fields_json,"
                        " confidence FROM detected_events WHERE filing_id=:id"
                        " ORDER BY severity, event_type"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            cards = _dicts(
                conn.execute(
                    text(
                        "SELECT id, card_type, title, summary, data_points, sentiment, confidence,"
                        " generated_at FROM insight_cards WHERE filing_id=:id ORDER BY id"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            validations = _dicts(
                conn.execute(
                    text(
                        "SELECT rule_name, passed, severity, message, checked_at"
                        " FROM validation_results WHERE filing_id=:id ORDER BY severity, rule_name"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            documents = _dicts(
                conn.execute(
                    text(
                        "SELECT id, doc_type, url, file_size, checksum, downloaded_at, parse_status"
                        " FROM source_documents WHERE filing_id=:id ORDER BY id"
                    ),
                    {"id": filing_id},
                ).fetchall()
            )
            pipeline = _dicts(
                conn.execute(
                    text(
                        "SELECT stage, status, started_at, finished_at, error_message"
                        " FROM pipeline_runs WHERE filing_key=:filing_key ORDER BY id"
                    ),
                    {"filing_key": filing_key},
                ).fetchall()
            )

        evidence_by_fact: dict[int, list[dict[str, Any]]] = {}
        for item in evidence:
            evidence_by_fact.setdefault(item["fact_id"], []).append(item)
        for fact in facts:
            fact["evidence"] = evidence_by_fact.get(fact["id"], [])
        for metric in metrics:
            metric["inputs"] = self._json(metric.pop("inputs_json"), {})
        for event in events:
            event["related_fields"] = self._json(event.pop("related_fields_json"), [])
        for card in cards:
            card["data_points"] = self._json(card["data_points"], {})

        return {
            "filing": filing_data,
            "facts": facts,
            "evidence": evidence,
            "metrics": metrics,
            "comparisons": comparisons,
            "events": events,
            "insight_cards": cards,
            "validation": validations,
            "source_documents": documents,
            "pipeline_state": pipeline,
        }

    # Citation-bearing columns. local_path is deliberately absent: internal
    # filesystem paths must never be handed out as citations.
    _CHUNK_COLUMNS = (
        "dc.id, dc.doc_id, dc.page_number, ds.section_type,"
        " ds.title AS section_title, dc.content, dc.importance_score,"
        " sd.checksum, sd.url AS source_url"
    )
    _CHUNK_JOINS = (
        " FROM document_chunks dc"
        " JOIN source_documents sd ON sd.id=dc.doc_id"
        " JOIN filings f ON f.id=sd.filing_id"
        " LEFT JOIN document_sections ds ON ds.id=dc.section_id"
    )

    def get_chunks(
        self,
        filing_key: str,
        limit: int,
        *,
        sections: list[str] | None = None,
        question_embedding: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """Return evidence chunks, optionally filtered and ranked by relevance.

        `sections` narrows to the named section types and is always available.
        `question_embedding` ranks by cosine distance against stored embeddings;
        when a filing has none it degrades to importance order rather than
        returning nothing, so a filing that has not been embedded still answers.

        Results are deduplicated by content. The ingestion pipeline currently
        stores the same text many times over (94% of rows in the present data
        set are redundant copies), and without this the caller's bounded chunk
        budget would be spent returning one passage repeatedly.
        """
        params: dict[str, Any] = {"filing_key": filing_key, "limit": limit}
        where = " WHERE f.filing_key=:filing_key"
        if sections:
            where += " AND ds.section_type = ANY(:sections)"
            params["sections"] = list(sections)

        if question_embedding is not None and self._has_embeddings(filing_key):
            params["query_vec"] = str(list(question_embedding))
            distance = "ce.embedding <=> CAST(:query_vec AS vector)"
            inner = (
                f"SELECT DISTINCT ON (dc.content) {self._CHUNK_COLUMNS},"
                f" 1 - ({distance}) AS retrieval_score"
                + self._CHUNK_JOINS
                + " JOIN chunk_embeddings ce ON ce.chunk_id = dc.id"
                + where
                + f" ORDER BY dc.content, {distance}, dc.id"
            )
            sql = f"SELECT * FROM ({inner}) t ORDER BY t.retrieval_score DESC, t.id LIMIT :limit"
        else:
            inner = (
                f"SELECT DISTINCT ON (dc.content) {self._CHUNK_COLUMNS},"
                " NULL::double precision AS retrieval_score"
                + self._CHUNK_JOINS
                + where
                + " ORDER BY dc.content, dc.importance_score DESC, dc.id"
            )
            sql = f"SELECT * FROM ({inner}) t ORDER BY t.importance_score DESC, t.id LIMIT :limit"

        with self.store.conn() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        return _dicts(rows)

    def _has_embeddings(self, filing_key: str) -> bool:
        with self.store.conn() as conn:
            return bool(
                conn.execute(
                    text(
                        "SELECT 1 FROM chunk_embeddings ce"
                        " JOIN document_chunks dc ON dc.id=ce.chunk_id"
                        " JOIN source_documents sd ON sd.id=dc.doc_id"
                        " JOIN filings f ON f.id=sd.filing_id"
                        " WHERE f.filing_key=:filing_key LIMIT 1"
                    ),
                    {"filing_key": filing_key},
                ).fetchone()
            )

    def known_section_types(self) -> list[str]:
        with self.store.conn() as conn:
            rows = conn.execute(
                text(
                    "SELECT DISTINCT section_type FROM document_sections"
                    " WHERE section_type IS NOT NULL ORDER BY section_type"
                )
            ).fetchall()
        return [row[0] for row in rows]

    @staticmethod
    def _json(value: str | None, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

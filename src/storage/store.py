"""
PostgreSQL storage layer using SQLAlchemy Core.
All SQL is executed via sqlalchemy.text() for explicit, auditable queries.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from src.domain.identity import FilingIdentity
from src.domain.models import Fact, InsightCard

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"

DEFAULT_DATABASE_URL = "postgresql+psycopg://financial:financial@localhost:5432/financial"


def resolve_database_url(database_url: str | None = None) -> str:
    """Return the connection URL, falling back to FR_DATABASE_URL then the default."""
    return database_url or os.getenv("FR_DATABASE_URL") or DEFAULT_DATABASE_URL


class FilingStore:
    """Manages all PostgreSQL persistence for the Financial Insight Engine."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = resolve_database_url(database_url)
        self.engine: Engine = create_engine(self.database_url, pool_pre_ping=True)
        self.init_db()

    def init_db(self) -> None:
        """Create all tables from schema.sql."""
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        # Strip line comments before splitting: statements are separated on ";",
        # so a semicolon inside a comment would otherwise become a statement.
        stripped = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
        with self.engine.begin() as conn:
            for statement in stripped.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
        logger.debug("Database initialised at %s", self.engine.url.render_as_string())

    @contextmanager
    def conn(self) -> Generator[Connection, None, None]:
        """Context manager that yields an open, auto-commit connection."""
        with self.engine.begin() as connection:
            yield connection

    # ------------------------------------------------------------------
    # Company
    # ------------------------------------------------------------------

    def upsert_company(self, stock_code: str, name_zh: str | None = None, **kwargs) -> int:
        """Insert or update a company. Returns company id."""
        with self.conn() as c:
            existing = c.execute(
                text("SELECT id FROM companies WHERE stock_code = :sc"),
                {"sc": stock_code},
            ).fetchone()
            if existing:
                c.execute(
                    text(
                        "UPDATE companies SET name_zh=COALESCE(:nz, name_zh),"
                        " name_en=COALESCE(:ne, name_en),"
                        " industry=COALESCE(:ind, industry),"
                        " market=COALESCE(:mkt, market)"
                        " WHERE stock_code=:sc"
                    ),
                    {
                        "nz": name_zh or kwargs.get("name_zh"),
                        "ne": kwargs.get("name_en"),
                        "ind": kwargs.get("industry"),
                        "mkt": kwargs.get("market"),
                        "sc": stock_code,
                    },
                )
                return existing[0]
            result = c.execute(
                text(
                    "INSERT INTO companies(stock_code, name_zh, name_en, industry, market)"
                    " VALUES(:sc,:nz,:ne,:ind,:mkt) RETURNING id"
                ),
                {
                    "sc": stock_code,
                    "nz": name_zh or kwargs.get("name_zh"),
                    "ne": kwargs.get("name_en"),
                    "ind": kwargs.get("industry"),
                    "mkt": kwargs.get("market"),
                },
            )
            return int(result.scalar_one())

    # ------------------------------------------------------------------
    # Filing
    # ------------------------------------------------------------------

    def upsert_filing(self, identity: FilingIdentity, company_id: int) -> int:
        """Insert or update a filing. Returns filing id."""
        with self.conn() as c:
            existing = c.execute(
                text("SELECT id FROM filings WHERE filing_key=:fk"),
                {"fk": identity.filing_key},
            ).fetchone()
            if existing:
                c.execute(
                    text("UPDATE filings SET updated_at=now() WHERE id=:id"),
                    {"id": existing[0]},
                )
                return existing[0]
            result = c.execute(
                text(
                    "INSERT INTO filings(filing_key, company_id, year, quarter, status)"
                    " VALUES(:fk,:cid,:yr,:qt,'pending') RETURNING id"
                ),
                {
                    "fk": identity.filing_key,
                    "cid": company_id,
                    "yr": identity.year,
                    "qt": identity.quarter,
                },
            )
            return int(result.scalar_one())

    def get_or_create_filing(self, identity: FilingIdentity, company_id: int) -> int:
        """Return existing filing id or create new one."""
        existing = self.get_filing_id(identity.filing_key)
        if existing is not None:
            return existing
        return self.upsert_filing(identity, company_id)

    def get_filing_id(self, filing_key: str) -> int | None:
        with self.conn() as c:
            row = c.execute(
                text("SELECT id FROM filings WHERE filing_key=:fk"),
                {"fk": filing_key},
            ).fetchone()
            return row[0] if row else None

    def get_filing_status(self, filing_key: str) -> str | None:
        with self.conn() as c:
            row = c.execute(
                text("SELECT status FROM filings WHERE filing_key=:fk"),
                {"fk": filing_key},
            ).fetchone()
            return row[0] if row else None

    def update_filing_status(self, filing_id: int, status: str) -> None:
        with self.conn() as c:
            c.execute(
                text("UPDATE filings SET status=:st, updated_at=now() WHERE id=:id"),
                {"st": status, "id": filing_id},
            )

    # ------------------------------------------------------------------
    # Source Documents
    # ------------------------------------------------------------------

    def save_source_doc(
        self,
        filing_id: int,
        doc_type: str,
        local_path: str | Path | None,
        url: str | None = None,
        file_size: int | None = None,
    ) -> int:
        lp = str(local_path) if local_path else None
        with self.conn() as c:
            # Check for existing
            existing = c.execute(
                text("SELECT id FROM source_documents WHERE filing_id=:fid AND doc_type=:dt"),
                {"fid": filing_id, "dt": doc_type},
            ).fetchone()
            if existing:
                c.execute(
                    text(
                        "UPDATE source_documents SET local_path=COALESCE(:lp, local_path),"
                        " url=COALESCE(:url, url), file_size=COALESCE(:fs, file_size),"
                        " downloaded_at=now()"
                        " WHERE id=:id"
                    ),
                    {"lp": lp, "url": url, "fs": file_size, "id": existing[0]},
                )
                return existing[0]
            result = c.execute(
                text(
                    "INSERT INTO source_documents"
                    "(filing_id, doc_type, local_path, url, file_size, downloaded_at, parse_status)"
                    " VALUES(:fid,:dt,:lp,:url,:fs,now(),'pending') RETURNING id"
                ),
                {"fid": filing_id, "dt": doc_type, "lp": lp, "url": url, "fs": file_size},
            )
            return int(result.scalar_one())

    # ------------------------------------------------------------------
    # Facts
    # ------------------------------------------------------------------

    def save_fact(self, filing_id: int, fact: Fact) -> int:
        """Upsert a single Fact. Returns fact id."""
        with self.conn() as c:
            existing = c.execute(
                text(
                    "SELECT id FROM financial_facts"
                    " WHERE filing_id=:fid AND field=:fld AND source_type=:st"
                ),
                {"fid": filing_id, "fld": fact.field, "st": fact.source_type},
            ).fetchone()
            params = {
                "fid": filing_id,
                "fld": fact.field,
                "val": fact.value,
                "unit": fact.unit,
                "ps": fact.period_start.isoformat() if fact.period_start else None,
                "pe": fact.period_end.isoformat() if fact.period_end else None,
                "pt": fact.period_type,
                "st": fact.source_type,
                "conf": fact.confidence,
                "xt": fact.xbrl_tag,
            }
            if existing:
                c.execute(
                    text(
                        "UPDATE financial_facts SET value=:val, unit=:unit,"
                        " period_start=:ps, period_end=:pe, period_type=:pt,"
                        " confidence=:conf, xbrl_tag=:xt"
                        " WHERE filing_id=:fid AND field=:fld AND source_type=:st"
                    ),
                    params,
                )
                return existing[0]
            result = c.execute(
                text(
                    "INSERT INTO financial_facts"
                    "(filing_id,field,value,unit,period_start,period_end,"
                    " period_type,source_type,confidence,xbrl_tag)"
                    " VALUES(:fid,:fld,:val,:unit,:ps,:pe,:pt,:st,:conf,:xt) RETURNING id"
                ),
                params,
            )
            return int(result.scalar_one())

    def save_facts_bulk(self, filing_id: int, facts: list[Fact]) -> None:
        """Upsert many Facts efficiently."""
        for fact in facts:
            try:
                self.save_fact(filing_id, fact)
            except Exception as exc:
                logger.warning("Failed to save fact %s: %s", fact.field, exc)

    # ------------------------------------------------------------------
    # Pages / Sections / Chunks
    # ------------------------------------------------------------------

    def save_page(
        self,
        doc_id: int,
        page_number: int,
        text_content: str,
        has_tables: bool = False,
    ) -> None:
        char_count = len(text_content)
        with self.conn() as c:
            c.execute(
                text(
                    "INSERT INTO document_pages"
                    "(doc_id, page_number, text_content, char_count, has_tables)"
                    " VALUES(:did,:pn,:tc,:cc,:ht)"
                    " ON CONFLICT (doc_id, page_number) DO UPDATE SET"
                    " text_content=EXCLUDED.text_content,"
                    " char_count=EXCLUDED.char_count, has_tables=EXCLUDED.has_tables"
                ),
                {
                    "did": doc_id,
                    "pn": page_number,
                    "tc": text_content,
                    "cc": char_count,
                    "ht": has_tables,
                },
            )

    def clear_document_text(self, doc_id: int) -> None:
        """Remove a document's derived pages, sections and chunks.

        Extraction is re-runnable, and these tables have no natural key to
        upsert against, so without clearing first a second run appends a whole
        new copy instead of replacing the old one. Chunks are removed before
        sections because chunk_embeddings and document_chunks reference them.
        """
        with self.conn() as c:
            c.execute(
                text(
                    "DELETE FROM chunk_embeddings WHERE chunk_id IN ("
                    " SELECT id FROM document_chunks WHERE doc_id=:did)"
                ),
                {"did": doc_id},
            )
            c.execute(text("DELETE FROM document_chunks WHERE doc_id=:did"), {"did": doc_id})
            c.execute(text("DELETE FROM document_sections WHERE doc_id=:did"), {"did": doc_id})
            c.execute(text("DELETE FROM document_pages WHERE doc_id=:did"), {"did": doc_id})

    def save_section(
        self,
        doc_id: int,
        section_type: str,
        title: str,
        page_start: int,
        page_end: int,
        content: str,
    ) -> int:
        with self.conn() as c:
            result = c.execute(
                text(
                    "INSERT INTO document_sections"
                    "(doc_id, section_type, title, page_start, page_end, content)"
                    " VALUES(:did,:st,:t,:ps,:pe,:ct) RETURNING id"
                ),
                {
                    "did": doc_id,
                    "st": section_type,
                    "t": title,
                    "ps": page_start,
                    "pe": page_end,
                    "ct": content,
                },
            )
            return int(result.scalar_one())

    def save_chunk(
        self,
        doc_id: int,
        section_id: int | None,
        page_number: int,
        chunk_index: int,
        content: str,
        **kwargs,
    ) -> int:
        with self.conn() as c:
            result = c.execute(
                text(
                    "INSERT INTO document_chunks"
                    "(doc_id,section_id,page_number,chunk_index,content,"
                    " char_offset_start,char_offset_end,contains_numbers,"
                    " contains_table,importance_score)"
                    " VALUES(:did,:sid,:pn,:ci,:ct,:cos,:coe,:cn,:ctb,:imp) RETURNING id"
                ),
                {
                    "did": doc_id,
                    "sid": section_id,
                    "pn": page_number,
                    "ci": chunk_index,
                    "ct": content,
                    "cos": kwargs.get("char_offset_start"),
                    "coe": kwargs.get("char_offset_end"),
                    "cn": bool(kwargs.get("contains_numbers")),
                    "ctb": bool(kwargs.get("contains_table")),
                    "imp": kwargs.get("importance_score", 0.5),
                },
            )
            return int(result.scalar_one())

    # ------------------------------------------------------------------
    # Metrics / Comparisons / Events
    # ------------------------------------------------------------------

    def save_metric(
        self,
        filing_id: int,
        metric_name: str,
        value: float,
        formula: str | None = None,
        inputs: dict | None = None,
    ) -> None:
        inputs_json = json.dumps(inputs) if inputs else None
        with self.conn() as c:
            c.execute(
                text(
                    "INSERT INTO financial_metrics"
                    "(filing_id, metric_name, value, formula, inputs_json)"
                    " VALUES(:fid,:mn,:val,:f,:ij)"
                    " ON CONFLICT (filing_id, metric_name) DO UPDATE SET"
                    " value=EXCLUDED.value, formula=EXCLUDED.formula,"
                    " inputs_json=EXCLUDED.inputs_json"
                ),
                {
                    "fid": filing_id,
                    "mn": metric_name,
                    "val": value,
                    "f": formula,
                    "ij": inputs_json,
                },
            )

    def save_comparison(
        self,
        filing_id: int,
        compare_filing_id: int | None,
        field: str,
        compare_type: str,
        current: float,
        prior: float,
    ) -> None:
        change_abs = current - prior
        change_pct = (change_abs / abs(prior) * 100) if prior != 0 else None
        direction = "up" if change_abs > 0 else ("down" if change_abs < 0 else "flat")
        if change_pct is not None:
            significance = (
                "large"
                if abs(change_pct) >= 10
                else ("moderate" if abs(change_pct) >= 3 else "small")
            )
        else:
            significance = "small"
        with self.conn() as c:
            c.execute(
                text(
                    "INSERT INTO period_comparisons"
                    "(filing_id,compare_filing_id,field,compare_type,"
                    " current_value,prior_value,change_abs,change_pct,direction,significance)"
                    " VALUES(:fid,:cfid,:fld,:ct,:cv,:pv,:ca,:cp,:dir,:sig)"
                ),
                {
                    "fid": filing_id,
                    "cfid": compare_filing_id,
                    "fld": field,
                    "ct": compare_type,
                    "cv": current,
                    "pv": prior,
                    "ca": change_abs,
                    "cp": change_pct,
                    "dir": direction,
                    "sig": significance,
                },
            )

    def save_event(
        self,
        filing_id: int,
        event_type: str,
        severity: str,
        title: str,
        description: str,
        **kwargs,
    ) -> None:
        related_json = json.dumps(kwargs.get("related_fields", []))
        with self.conn() as c:
            c.execute(
                text(
                    "INSERT INTO detected_events"
                    "(filing_id,event_type,severity,title,description,related_fields_json,confidence)"
                    " VALUES(:fid,:et,:sv,:t,:desc,:rf,:conf)"
                ),
                {
                    "fid": filing_id,
                    "et": event_type,
                    "sv": severity,
                    "t": title,
                    "desc": description,
                    "rf": related_json,
                    "conf": kwargs.get("confidence", 0.9),
                },
            )

    def save_insight_card(self, filing_id: int, card: InsightCard) -> int:
        data_json = json.dumps(card.data_points, ensure_ascii=False)
        with self.conn() as c:
            result = c.execute(
                text(
                    "INSERT INTO insight_cards"
                    "(filing_id,card_type,title,summary,data_points,sentiment,confidence)"
                    " VALUES(:fid,:ct,:t,:s,:dp,:sent,:conf) RETURNING id"
                ),
                {
                    "fid": filing_id,
                    "ct": card.card_type,
                    "t": card.title,
                    "s": card.summary,
                    "dp": data_json,
                    "sent": card.sentiment,
                    "conf": card.confidence,
                },
            )
            return int(result.scalar_one())

    def save_validation_result(
        self,
        filing_id: int,
        rule_name: str,
        passed: bool,
        severity: str,
        message: str,
    ) -> None:
        with self.conn() as c:
            c.execute(
                text(
                    "INSERT INTO validation_results"
                    "(filing_id,rule_name,passed,severity,message)"
                    " VALUES(:fid,:rn,:p,:sv,:msg)"
                ),
                {
                    "fid": filing_id,
                    "rn": rule_name,
                    "p": passed,
                    "sv": severity,
                    "msg": message,
                },
            )

    def log_pipeline_run(
        self,
        filing_key: str,
        stage: str,
        status: str,
        error: str | None = None,
    ) -> None:
        with self.conn() as c:
            if status == "started":
                c.execute(
                    text("INSERT INTO pipeline_runs(filing_key,stage,status) VALUES(:fk,:st,:s)"),
                    {"fk": filing_key, "st": stage, "s": status},
                )
            else:
                c.execute(
                    text(
                        "UPDATE pipeline_runs SET status=:s,"
                        " finished_at=now(), error_message=:err"
                        " WHERE filing_key=:fk AND stage=:st"
                        "   AND status='started'"
                    ),
                    {"s": status, "err": error, "fk": filing_key, "st": stage},
                )

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_facts(self, filing_key: str, fields: list[str] | None = None) -> list[dict]:
        """Return list of fact dicts for a filing."""
        with self.conn() as c:
            if fields:
                placeholders = ",".join(f":f{i}" for i in range(len(fields)))
                params: dict = {"fk": filing_key}
                params.update({f"f{i}": f for i, f in enumerate(fields)})
                rows = c.execute(
                    text(
                        f"SELECT ff.field, ff.value, ff.unit, ff.source_type, ff.confidence,"
                        f" ff.period_start, ff.period_end, ff.xbrl_tag"
                        f" FROM financial_facts ff"
                        f" JOIN filings fl ON fl.id=ff.filing_id"
                        f" WHERE fl.filing_key=:fk AND ff.field IN ({placeholders})"
                        f" ORDER BY ff.source_type, ff.field"
                    ),
                    params,
                ).fetchall()
            else:
                rows = c.execute(
                    text(
                        "SELECT ff.field, ff.value, ff.unit, ff.source_type, ff.confidence,"
                        " ff.period_start, ff.period_end, ff.xbrl_tag"
                        " FROM financial_facts ff"
                        " JOIN filings fl ON fl.id=ff.filing_id"
                        " WHERE fl.filing_key=:fk"
                        " ORDER BY ff.source_type, ff.field"
                    ),
                    {"fk": filing_key},
                ).fetchall()
        columns = [
            "field",
            "value",
            "unit",
            "source_type",
            "confidence",
            "period_start",
            "period_end",
            "xbrl_tag",
        ]
        return [dict(zip(columns, row)) for row in rows]

    def get_facts_dict(self, filing_key: str) -> dict[str, float]:
        """Return {field: value} mapping, preferring XBRL source."""
        facts = self.get_facts(filing_key)
        # Priority: xbrl > ixbrl > pdf_table > pdf_text > computed
        priority = {"xbrl": 0, "ixbrl": 1, "pdf_table": 2, "pdf_text": 3, "computed": 4}
        best: dict[str, tuple[float, int]] = {}
        for f in facts:
            field = f["field"]
            rank = priority.get(f["source_type"], 99)
            if field not in best or rank < best[field][1]:
                best[field] = (f["value"], rank)
        return {field: val for field, (val, _) in best.items()}

    def get_chunks(self, filing_key: str, section_type: str | None = None) -> list[dict]:
        with self.conn() as c:
            if section_type:
                rows = c.execute(
                    text(
                        "SELECT dc.id, dc.content, dc.page_number, dc.chunk_index,"
                        " ds.section_type, ds.title, dc.contains_numbers, dc.contains_table,"
                        " dc.importance_score"
                        " FROM document_chunks dc"
                        " JOIN document_sections ds ON ds.id=dc.section_id"
                        " JOIN source_documents sd ON sd.id=dc.doc_id"
                        " JOIN filings fl ON fl.id=sd.filing_id"
                        " WHERE fl.filing_key=:fk AND ds.section_type=:st"
                        " ORDER BY dc.page_number, dc.chunk_index"
                    ),
                    {"fk": filing_key, "st": section_type},
                ).fetchall()
            else:
                rows = c.execute(
                    text(
                        "SELECT dc.id, dc.content, dc.page_number, dc.chunk_index,"
                        " ds.section_type, ds.title, dc.contains_numbers, dc.contains_table,"
                        " dc.importance_score"
                        " FROM document_chunks dc"
                        " LEFT JOIN document_sections ds ON ds.id=dc.section_id"
                        " JOIN source_documents sd ON sd.id=dc.doc_id"
                        " JOIN filings fl ON fl.id=sd.filing_id"
                        " WHERE fl.filing_key=:fk"
                        " ORDER BY dc.page_number, dc.chunk_index"
                    ),
                    {"fk": filing_key},
                ).fetchall()
        columns = [
            "id",
            "content",
            "page_number",
            "chunk_index",
            "section_type",
            "section_title",
            "contains_numbers",
            "contains_table",
            "importance_score",
        ]
        return [dict(zip(columns, row)) for row in rows]

    def get_insight_cards(self, filing_key: str) -> list[dict]:
        with self.conn() as c:
            rows = c.execute(
                text(
                    "SELECT ic.id, ic.card_type, ic.title, ic.summary,"
                    " ic.data_points, ic.sentiment, ic.confidence, ic.generated_at"
                    " FROM insight_cards ic"
                    " JOIN filings fl ON fl.id=ic.filing_id"
                    " WHERE fl.filing_key=:fk"
                    " ORDER BY ic.generated_at"
                ),
                {"fk": filing_key},
            ).fetchall()
        columns = [
            "id",
            "card_type",
            "title",
            "summary",
            "data_points",
            "sentiment",
            "confidence",
            "generated_at",
        ]
        result = []
        for row in rows:
            d = dict(zip(columns, row))
            try:
                d["data_points"] = json.loads(d["data_points"]) if d["data_points"] else {}
            except json.JSONDecodeError:
                d["data_points"] = {}
            result.append(d)
        return result

    def get_metrics(self, filing_key: str) -> list[dict]:
        with self.conn() as c:
            rows = c.execute(
                text(
                    "SELECT fm.metric_name, fm.value, fm.formula, fm.inputs_json, fm.confidence"
                    " FROM financial_metrics fm"
                    " JOIN filings fl ON fl.id=fm.filing_id"
                    " WHERE fl.filing_key=:fk"
                    " ORDER BY fm.metric_name"
                ),
                {"fk": filing_key},
            ).fetchall()
        columns = ["metric_name", "value", "formula", "inputs_json", "confidence"]
        result = []
        for row in rows:
            d = dict(zip(columns, row))
            try:
                d["inputs"] = json.loads(d["inputs_json"]) if d["inputs_json"] else {}
            except json.JSONDecodeError:
                d["inputs"] = {}
            result.append(d)
        return result

    def get_comparisons(self, filing_key: str, compare_type: str | None = None) -> list[dict]:
        with self.conn() as c:
            if compare_type:
                rows = c.execute(
                    text(
                        "SELECT pc.field, pc.compare_type, pc.current_value, pc.prior_value,"
                        " pc.change_abs, pc.change_pct, pc.direction, pc.significance"
                        " FROM period_comparisons pc"
                        " JOIN filings fl ON fl.id=pc.filing_id"
                        " WHERE fl.filing_key=:fk AND pc.compare_type=:ct"
                    ),
                    {"fk": filing_key, "ct": compare_type},
                ).fetchall()
            else:
                rows = c.execute(
                    text(
                        "SELECT pc.field, pc.compare_type, pc.current_value, pc.prior_value,"
                        " pc.change_abs, pc.change_pct, pc.direction, pc.significance"
                        " FROM period_comparisons pc"
                        " JOIN filings fl ON fl.id=pc.filing_id"
                        " WHERE fl.filing_key=:fk"
                    ),
                    {"fk": filing_key},
                ).fetchall()
        columns = [
            "field",
            "compare_type",
            "current_value",
            "prior_value",
            "change_abs",
            "change_pct",
            "direction",
            "significance",
        ]
        return [dict(zip(columns, row)) for row in rows]

    def get_events(self, filing_key: str) -> list[dict]:
        with self.conn() as c:
            rows = c.execute(
                text(
                    "SELECT de.event_type, de.severity, de.title, de.description,"
                    " de.related_fields_json, de.confidence"
                    " FROM detected_events de"
                    " JOIN filings fl ON fl.id=de.filing_id"
                    " WHERE fl.filing_key=:fk"
                    " ORDER BY de.severity, de.event_type"
                ),
                {"fk": filing_key},
            ).fetchall()
        columns = [
            "event_type",
            "severity",
            "title",
            "description",
            "related_fields_json",
            "confidence",
        ]
        result = []
        for row in rows:
            d = dict(zip(columns, row))
            try:
                d["related_fields"] = json.loads(d["related_fields_json"] or "[]")
            except json.JSONDecodeError:
                d["related_fields"] = []
            result.append(d)
        return result

    def get_validation_results(self, filing_key: str) -> list[dict]:
        with self.conn() as c:
            rows = c.execute(
                text(
                    "SELECT vr.rule_name, vr.passed, vr.severity, vr.message"
                    " FROM validation_results vr"
                    " JOIN filings fl ON fl.id=vr.filing_id"
                    " WHERE fl.filing_key=:fk"
                    " ORDER BY vr.severity, vr.rule_name"
                ),
                {"fk": filing_key},
            ).fetchall()
        columns = ["rule_name", "passed", "severity", "message"]
        return [dict(zip(columns, row)) for row in rows]

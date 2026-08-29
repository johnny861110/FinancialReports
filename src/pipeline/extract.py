"""
Pipeline stage 2: Extract — parse sources and store facts, pages, sections, chunks.
CPU-bound PDF work runs in a ThreadPoolExecutor so it doesn't block the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.identity import FilingIdentity
from src.domain.models import Fact
from src.normalize.fact_mapper import map_facts
from src.normalize.period_normalizer import quarter_to_dates

if TYPE_CHECKING:
    from src.storage.store import FilingStore

logger = logging.getLogger(__name__)

# Shared thread pool for CPU-bound PDF work (one worker keeps memory bounded)
_PDF_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pdf_parse")


async def run_extract_async(
    identity: FilingIdentity,
    store: FilingStore,
    doc_paths: dict,
    force: bool = False,
) -> dict:
    """
    Async pipeline stage 2.
    XBRL parsing and PDF text extraction run in thread pool to avoid blocking.
    """
    fk = identity.filing_key
    loop = asyncio.get_running_loop()
    store.log_pipeline_run(fk, "extract", "started")

    try:
        current_status = await loop.run_in_executor(None, store.get_filing_status, fk)
        if current_status == "extracted" and not force:
            logger.info("Skipping extract for %s — already extracted", fk)
            store.log_pipeline_run(fk, "extract", "skipped")
            return {"facts_count": 0, "chunks_count": 0, "status": "skipped"}

        filing_id = await loop.run_in_executor(None, store.get_filing_id, fk)
        if filing_id is None:
            raise ValueError(f"Filing not found: {fk}. Run ingest first.")

        xbrl_path: Path | None = doc_paths.get("xbrl_path")
        ixbrl_path: Path | None = doc_paths.get("ixbrl_path")
        pdf_path: Path | None = doc_paths.get("pdf_path")

        facts_count = 0
        has_xbrl = False

        # ── XBRL / iXBRL parsing (offload to thread) ──────────────────────────
        if xbrl_path and Path(xbrl_path).exists():
            facts_count, has_xbrl = await loop.run_in_executor(
                _PDF_EXECUTOR, _parse_xbrl_sync, fk, filing_id, identity, xbrl_path, store
            )

        if not has_xbrl and ixbrl_path and Path(ixbrl_path).exists():
            facts_count, has_xbrl = await loop.run_in_executor(
                _PDF_EXECUTOR, _parse_ixbrl_sync, fk, filing_id, identity, ixbrl_path, store
            )

        # ── FinMind API fallback (scrape structured data when XBRL unavailable) ─
        if not has_xbrl:
            fm_count = await _fetch_finmind_facts(identity, filing_id, store)
            if fm_count:
                facts_count = fm_count
                has_xbrl = True  # treat as authoritative for PDF table fallback

        # ── PDF text extraction (offload to thread) ────────────────────────────
        chunks_count = 0
        if pdf_path and Path(pdf_path).exists():
            chunks_count = await loop.run_in_executor(
                _PDF_EXECUTOR,
                _extract_pdf_sync,
                fk,
                filing_id,
                identity,
                pdf_path,
                has_xbrl,
                store,
            )

        await loop.run_in_executor(None, store.update_filing_status, filing_id, "extracted")
        store.log_pipeline_run(fk, "extract", "completed")

        return {"facts_count": facts_count, "chunks_count": chunks_count, "status": "completed"}

    except Exception as exc:
        logger.error("Extract failed for %s: %s", fk, exc, exc_info=True)
        store.log_pipeline_run(fk, "extract", "failed", error=str(exc))
        raise


# ── FinMind async fetch ────────────────────────────────────────────────────────


async def _fetch_finmind_facts(
    identity: FilingIdentity,
    filing_id: int,
    store,
) -> int:
    """Fetch facts from FinMind API and save to DB. Returns number of facts saved."""
    from src.normalize.period_normalizer import quarter_to_dates
    from src.sources.finmind_client import FinMindClient

    try:
        client = FinMindClient()
        raw_facts = await client.fetch_facts_async(identity)
    except Exception as exc:
        logger.warning("FinMind fetch failed for %s: %s", identity.filing_key, exc)
        return 0

    if not raw_facts:
        return 0

    period_start, period_end = quarter_to_dates(identity)
    fact_objects = [
        Fact(
            filing_key=identity.filing_key,
            field=f["field"],
            value=f["value"],
            unit=f["unit"],
            period_start=period_end if f["period_type"] == "instant" else period_start,
            period_end=period_end,
            period_type=f["period_type"],
            source_type="finmind",
            confidence=f["confidence"],
            xbrl_tag=f.get("xbrl_tag"),
        )
        for f in raw_facts
    ]
    store.save_facts_bulk(filing_id, fact_objects)
    logger.info("Saved %d FinMind facts for %s", len(fact_objects), identity.filing_key)
    return len(fact_objects)


# ── sync workers (run inside thread pool) ─────────────────────────────────────


def _parse_xbrl_sync(
    fk: str, filing_id: int, identity: FilingIdentity, xbrl_path, store
) -> tuple[int, bool]:
    from src.parsers.xbrl_parser import parse_xbrl

    raw_facts = parse_xbrl(Path(xbrl_path), identity)
    return _save_canonical_facts(fk, filing_id, identity, raw_facts, "xbrl", 1.0, store)


def _parse_ixbrl_sync(
    fk: str, filing_id: int, identity: FilingIdentity, ixbrl_path, store
) -> tuple[int, bool]:
    from src.parsers.ixbrl_parser import parse_ixbrl

    raw_facts = parse_ixbrl(Path(ixbrl_path), identity)
    return _save_canonical_facts(fk, filing_id, identity, raw_facts, "ixbrl", 0.95, store)


def _save_canonical_facts(
    fk, filing_id, identity, raw_facts, source_type, default_confidence, store
) -> tuple[int, bool]:
    canonical = map_facts(raw_facts)
    if not canonical:
        return 0, False
    period_start, period_end = quarter_to_dates(identity)
    fact_objects = [
        Fact(
            filing_key=fk,
            field=f["field"],
            value=f["value"],
            unit=f["unit"],
            period_start=f.get("period_start") or period_start,
            period_end=f.get("period_end") or period_end,
            period_type=f.get("period_type", "duration"),
            source_type=source_type,
            confidence=f.get("confidence", default_confidence),
            xbrl_tag=f.get("xbrl_tag"),
        )
        for f in canonical
    ]
    store.save_facts_bulk(filing_id, fact_objects)
    logger.info("Saved %d %s facts for %s", len(fact_objects), source_type, fk)
    return len(fact_objects), True


def _extract_pdf_sync(
    fk: str, filing_id: int, identity: FilingIdentity, pdf_path, has_xbrl: bool, store
) -> int:
    from sqlalchemy import text

    from src.parsers.pdf_section_parser import build_chunks, split_sections
    from src.parsers.pdf_text_parser import extract_pages

    pages = extract_pages(Path(pdf_path))
    if not pages:
        return 0

    # Get or create PDF source_doc record
    with store.conn() as c:
        row = c.execute(
            text("SELECT id FROM source_documents WHERE filing_id=:fid AND doc_type='pdf'"),
            {"fid": filing_id},
        ).fetchone()
    doc_id = row[0] if row else store.save_source_doc(filing_id, "pdf", pdf_path)

    # Save pages
    for page in pages:
        store.save_page(doc_id, page.page_number, page.text, page.has_tables)

    # Split into sections and save
    sections = split_sections(pages)
    section_id_map: dict[int, int] = {}
    for i, section in enumerate(sections):
        sec_id = store.save_section(
            doc_id,
            section.section_type,
            section.title,
            section.page_start,
            section.page_end,
            section.content,
        )
        section_id_map[i] = sec_id

    # PDF table fallback when no XBRL
    if not has_xbrl:
        _pdf_table_fallback(filing_id, fk, identity, store, Path(pdf_path), sections)

    # Build RAG chunks
    raw_chunks = build_chunks(sections)
    chunks_count = 0
    # Attribute each chunk to the section that produced it, by index. Matching
    # on (section_type, section_title) instead wrote every chunk once per
    # section sharing that pair, which duplicated the corpus by up to 170x.
    for chunk in raw_chunks:
        store.save_chunk(
            doc_id=doc_id,
            section_id=section_id_map.get(chunk["section_index"]),
            page_number=chunk["page_start"],
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            char_offset_start=chunk.get("char_offset_start"),
            char_offset_end=chunk.get("char_offset_end"),
            contains_numbers=chunk.get("contains_numbers", False),
            contains_table=chunk.get("contains_table", False),
            importance_score=chunk.get("importance_score", 0.5),
        )
        chunks_count += 1

    logger.info("%s: %d pages, %d sections, %d chunks", fk, len(pages), len(sections), chunks_count)
    return chunks_count


def _pdf_table_fallback(filing_id, fk, identity, store, pdf_path: Path, sections) -> None:
    from src.domain.taxonomy import ALL_CANONICAL, CANONICAL_BALANCE
    from src.normalize.period_normalizer import quarter_to_dates
    from src.parsers.pdf_table_parser import extract_financial_tables, tables_to_facts

    # Extra synonyms for common Chinese financial terms that differ slightly
    # between companies (e.g. 總計 vs 總額, 合計 vs 總額)
    _SYNONYMS: dict[str, list[str]] = {
        "total_assets": ["資產總計", "資產合計", "資產總額"],
        "total_liabilities": ["負債總計", "負債合計", "負債總額"],
        "equity": ["權益總計", "權益合計", "權益總額", "股東權益合計"],
        "current_assets": ["流動資產合計", "流動資產總計"],
        "current_liabilities": ["流動負債合計", "流動負債總計"],
        "net_revenue": ["營業收入", "營業收入合計", "營收"],
        "operating_income": ["營業利益", "營業利益（損失）"],
        "net_income": ["本期淨利", "本期淨利（淨損）", "稅後淨利"],
    }
    _SYNONYM_TO_FIELD = {zh: field for field, zhs in _SYNONYMS.items() for zh in zhs}

    period_start, period_end = quarter_to_dates(identity)
    instant_fields = {f for f in CANONICAL_BALANCE}

    for section in sections:
        if section.section_type not in ("income_statement", "balance_sheet", "cash_flow"):
            continue
        rows = extract_financial_tables(pdf_path, section.page_start, section.page_end)
        for raw in tables_to_facts(rows):
            label = raw["label"]
            field = None
            # 1. Direct taxonomy match
            for f, meta in ALL_CANONICAL.items():
                if meta["zh"] in label or label in meta["zh"]:
                    field = f
                    break
            # 2. Synonym match
            if field is None:
                for zh, f in _SYNONYM_TO_FIELD.items():
                    if zh in label:
                        field = f
                        break
            if field is None:
                continue
            period_type = "instant" if field in instant_fields else "duration"
            fact = Fact(
                filing_key=fk,
                field=field,
                value=raw["value"],
                unit="TWD_thousands",
                period_start=period_end if period_type == "instant" else period_start,
                period_end=period_end,
                period_type=period_type,
                source_type="pdf_table",
                confidence=0.75,
            )
            store.save_fact(filing_id, fact)


# ── sync wrapper ───────────────────────────────────────────────────────────────


def run_extract(
    identity: FilingIdentity,
    store: FilingStore,
    doc_paths: dict,
    force: bool = False,
) -> dict:
    """Sync entry-point — runs the async implementation."""
    return asyncio.run(run_extract_async(identity, store, doc_paths, force=force))

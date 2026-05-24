"""
Pipeline stage 1: Ingest — download XBRL and PDF source documents (async).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from src.domain.identity import FilingIdentity
from src.normalize.company_mapper import resolve_company
from src.sources.registry import get_mops_client, get_pdf_client, get_xbrl_client

if TYPE_CHECKING:
    from src.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


async def run_ingest_async(
    identity: FilingIdentity,
    store: SQLiteStore,
    output_dir: Path,
    force: bool = False,
    local_pdf_dir: Path | None = None,
) -> dict:
    """
    Async pipeline stage 1.

    XBRL and PDF downloads run in parallel via asyncio.gather.
    A shared httpx.AsyncClient is reused for all requests (single connection pool).
    """
    fk = identity.filing_key
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_running_loop()
    store.log_pipeline_run(fk, "ingest", "started")

    try:
        current_status = await loop.run_in_executor(None, store.get_filing_status, fk)
        if current_status not in (None, "pending") and not force:
            logger.info("Skipping ingest for %s — already %s", fk, current_status)
            store.log_pipeline_run(fk, "ingest", "skipped")
            return {"status": "skipped", "xbrl_path": None, "ixbrl_path": None, "pdf_path": None}

        # 1. Resolve company and upsert filing (sync, fast)
        mops_client = get_mops_client()
        company_id, company_name = await loop.run_in_executor(
            None, resolve_company, identity.stock_code, store, mops_client
        )
        filing_id = await loop.run_in_executor(None, store.upsert_filing, identity, company_id)
        logger.info("Filing id=%d (%s %s)", filing_id, identity.stock_code, company_name)

        # 2. Parallel async downloads: XBRL (x2) + PDF
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http:
            xbrl_task = _try_xbrl(identity, output_dir, http)
            ixbrl_task = _try_ixbrl(identity, output_dir, http)
            pdf_task = _fetch_pdf(identity, output_dir, local_pdf_dir, http)

            xbrl_path, ixbrl_path, pdf_path = await asyncio.gather(
                xbrl_task, ixbrl_task, pdf_task, return_exceptions=False
            )

        # 3. Save source_documents records
        for doc_type, path in [("xbrl", xbrl_path), ("ixbrl", ixbrl_path), ("pdf", pdf_path)]:
            if path:
                await loop.run_in_executor(
                    None,
                    store.save_source_doc,
                    filing_id,
                    doc_type,
                    path,
                    None,
                    path.stat().st_size,
                )

        # 4. Update status
        await loop.run_in_executor(None, store.update_filing_status, filing_id, "ingested")
        store.log_pipeline_run(fk, "ingest", "completed")

        return {
            "xbrl_path": xbrl_path,
            "ixbrl_path": ixbrl_path,
            "pdf_path": pdf_path,
            "filing_id": filing_id,
            "status": "completed",
        }

    except Exception as exc:
        logger.error("Ingest failed for %s: %s", fk, exc, exc_info=True)
        store.log_pipeline_run(fk, "ingest", "failed", error=str(exc))
        raise


# ── helpers ────────────────────────────────────────────────────────────────────


async def _try_xbrl(
    identity: FilingIdentity, output_dir: Path, client: httpx.AsyncClient
) -> Path | None:
    try:
        return await get_xbrl_client().download_xbrl_async(identity, output_dir, client)
    except Exception as exc:
        logger.debug("XBRL unavailable for %s: %s", identity.filing_key, exc)
        return None


async def _try_ixbrl(
    identity: FilingIdentity, output_dir: Path, client: httpx.AsyncClient
) -> Path | None:
    try:
        return await get_xbrl_client().download_ixbrl_async(identity, output_dir, client)
    except Exception as exc:
        logger.debug("iXBRL unavailable for %s: %s", identity.filing_key, exc)
        return None


async def _fetch_pdf(
    identity: FilingIdentity,
    output_dir: Path,
    local_pdf_dir: Path | None,
    client: httpx.AsyncClient,
) -> Path | None:
    # Check local cache first (data/financial_reports)
    candidates = []
    if local_pdf_dir:
        candidates.append(Path(local_pdf_dir) / identity.pdf_filename)
    candidates.append(Path("data/financial_reports") / identity.pdf_filename)

    for p in candidates:
        if p.exists() and p.stat().st_size > 1024:
            logger.info("Using local PDF: %s", p)
            return p

    # Download from TWSE
    try:
        return await get_pdf_client().download_async(identity, output_dir, client)
    except Exception as exc:
        logger.warning("PDF download failed for %s: %s", identity.filing_key, exc)
        return None


# ── sync wrapper ───────────────────────────────────────────────────────────────


def run_ingest(
    identity: FilingIdentity,
    store: SQLiteStore,
    output_dir: Path,
    force: bool = False,
    local_pdf_dir: Path | None = None,
) -> dict:
    """Sync entry-point — runs the async implementation."""
    return asyncio.run(
        run_ingest_async(identity, store, output_dir, force=force, local_pdf_dir=local_pdf_dir)
    )

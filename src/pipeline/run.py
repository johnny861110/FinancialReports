"""
Orchestrates the full pipeline: ingest → extract → validate → insights.
Async-first; sync wrapper available for backward compat.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.identity import FilingIdentity

if TYPE_CHECKING:
    from src.storage.store import FilingStore

logger = logging.getLogger(__name__)

STAGES = ["ingest", "extract", "validate", "insights"]

_STAGE_STATUS = {
    "ingest": "ingested",
    "extract": "extracted",
    "validate": "validated",
    "insights": "insight_ready",
}


# ── single filing ──────────────────────────────────────────────────────────────


async def run_pipeline_async(
    identity: FilingIdentity,
    store: FilingStore,
    output_dir: Path,
    stages: list[str] | None = None,
    force: bool = False,
) -> dict:
    """
    Run pipeline stages in order for one filing.
    Each stage is idempotent — already-completed stages are skipped unless force=True.
    """
    output_dir = Path(output_dir)
    fk = identity.filing_key
    stages_to_run = stages or STAGES
    results: dict[str, dict] = {}
    loop = asyncio.get_running_loop()

    for stage in stages_to_run:
        if stage not in STAGES:
            raise ValueError(f"Unknown stage: {stage}. Valid: {STAGES}")

    doc_paths: dict = {}

    for stage in stages_to_run:
        # Idempotency check
        current_status = await loop.run_in_executor(None, store.get_filing_status, fk)
        target_status = _STAGE_STATUS[stage]
        if not force and _status_reached(current_status, target_status):
            logger.info("Stage '%s' already done for %s — skipping", stage, fk)
            results[stage] = {"status": "skipped"}
            continue

        logger.info("Running stage '%s' for %s", stage, fk)
        try:
            if stage == "ingest":
                from src.pipeline.ingest import run_ingest_async

                result = await run_ingest_async(
                    identity,
                    store,
                    output_dir,
                    force=force,
                    local_pdf_dir=Path("data/financial_reports"),
                )
                doc_paths = {k: result.get(k) for k in ("xbrl_path", "ixbrl_path", "pdf_path")}

            elif stage == "extract":
                if not doc_paths:
                    doc_paths = await loop.run_in_executor(
                        None, _recover_doc_paths, identity, store
                    )
                from src.pipeline.extract import run_extract_async

                result = await run_extract_async(identity, store, doc_paths, force=force)

            elif stage == "validate":
                from src.pipeline.validate import run_validate

                result = await loop.run_in_executor(None, run_validate, identity, store)

            elif stage == "insights":
                from src.pipeline.build_insights import run_build_insights

                result = await loop.run_in_executor(None, run_build_insights, identity, store)

            results[stage] = result
            logger.info("Stage '%s' done for %s: %s", stage, fk, result.get("status"))

        except Exception as exc:
            logger.error("Stage '%s' failed for %s: %s", stage, fk, exc, exc_info=True)
            results[stage] = {"status": "failed", "error": str(exc)}
            break  # stop on failure

    return results


# ── batch with controlled concurrency ─────────────────────────────────────────


async def run_batch_async(
    filings: list[FilingIdentity],
    store: FilingStore,
    output_dir: Path,
    stages: list[str] | None = None,
    force: bool = False,
    concurrency: int = 4,
) -> list[dict]:
    """
    Process multiple filings concurrently, capped at `concurrency` at a time.
    Returns list of result dicts (one per filing, in order).
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_one(identity: FilingIdentity) -> dict:
        async with semaphore:
            try:
                result = await run_pipeline_async(
                    identity, store, output_dir, stages=stages, force=force
                )
                return {"filing_key": identity.filing_key, "results": result}
            except Exception as exc:
                return {"filing_key": identity.filing_key, "error": str(exc)}

    tasks = [_run_one(identity) for identity in filings]
    return await asyncio.gather(*tasks)


# ── sync wrappers ──────────────────────────────────────────────────────────────


def run_pipeline(
    identity: FilingIdentity,
    store: FilingStore,
    output_dir: Path,
    stages: list[str] | None = None,
    force: bool = False,
) -> dict:
    """Sync entry-point — runs the async pipeline."""
    return asyncio.run(run_pipeline_async(identity, store, output_dir, stages=stages, force=force))


# ── helpers ────────────────────────────────────────────────────────────────────


def _status_reached(current: str | None, target: str) -> bool:
    """Return True if the filing status already meets or exceeds the target."""
    order = {
        s: i
        for i, s in enumerate(["pending", "ingested", "extracted", "validated", "insight_ready"])
    }
    cur_rank = order.get(current or "pending", 0)
    tgt_rank = order.get(target, 0)
    return cur_rank >= tgt_rank


def _recover_doc_paths(identity: FilingIdentity, store: FilingStore) -> dict:
    filing_id = store.get_filing_id(identity.filing_key)
    if filing_id is None:
        return {}
    from sqlalchemy import text

    paths: dict = {}
    with store.conn() as c:
        rows = c.execute(
            text(
                "SELECT doc_type, local_path FROM source_documents"
                " WHERE filing_id=:fid AND local_path IS NOT NULL"
            ),
            {"fid": filing_id},
        ).fetchall()
    for doc_type, local_path in rows:
        if local_path:
            p = Path(local_path)
            if p.exists():
                key = {"xbrl": "xbrl_path", "ixbrl": "ixbrl_path", "pdf": "pdf_path"}.get(doc_type)
                if key:
                    paths[key] = p
    return paths

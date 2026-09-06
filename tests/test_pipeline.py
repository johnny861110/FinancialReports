"""Pipeline stage behaviour that is not covered by the storage or API suites.

These tests never reach the network: the per-source download helpers in
src.pipeline.ingest are patched, which is also the only way to reproduce the
"every source returned nothing" case deterministically.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from src.domain.identity import FilingIdentity
from src.pipeline import ingest as ingest_module
from src.pipeline.ingest import run_ingest_async
from src.storage.store import FilingStore

STOCK = "2330"


@pytest.fixture
def store(database_url):
    return FilingStore(database_url)


def _no_downloads(monkeypatch, store, company_id):
    """Every source yields nothing, and company resolution stays offline."""

    async def _none(*args, **kwargs):
        return None

    monkeypatch.setattr(ingest_module, "get_mops_client", lambda: None)
    monkeypatch.setattr(
        ingest_module, "resolve_company", lambda code, s, client: (company_id, "台積電")
    )
    monkeypatch.setattr(ingest_module, "_try_xbrl", _none)
    monkeypatch.setattr(ingest_module, "_try_ixbrl", _none)
    monkeypatch.setattr(ingest_module, "_fetch_pdf", _none)


async def test_ingest_fails_when_no_source_document_is_obtained(store, monkeypatch, tmp_path):
    """A stage that downloaded nothing must not report success.

    Each download is individually optional -- a filing may legitimately have no
    XBRL -- so all three returning None used to be indistinguishable from a good
    run. The filing was marked "ingested", extract then had nothing to read, and
    insights still produced cards from the FinMind fact fallback, leaving
    filings at "insight_ready" with a quality score and no retrievable text.
    """
    identity = FilingIdentity(stock_code=STOCK, year=2025, quarter="Q1")
    company_id = store.upsert_company(STOCK, name_zh="台積電")
    _no_downloads(monkeypatch, store, company_id)

    with pytest.raises(RuntimeError, match="no source document"):
        await run_ingest_async(identity, store, tmp_path)

    assert store.get_filing_status(identity.filing_key) == "pending"


async def test_failed_ingest_leaves_the_filing_retryable(store, monkeypatch, tmp_path):
    """The filing must not land in a state a later non-forced run skips.

    run_pipeline_async skips any stage whose target status is already reached,
    so advancing the status here would make the filing permanently unfixable
    without --force.
    """
    identity = FilingIdentity(stock_code=STOCK, year=2025, quarter="Q1")
    company_id = store.upsert_company(STOCK, name_zh="台積電")
    _no_downloads(monkeypatch, store, company_id)

    with pytest.raises(RuntimeError):
        await run_ingest_async(identity, store, tmp_path)

    assert store.get_filing_status(identity.filing_key) != "ingested"
    with store.conn() as conn:
        statuses = [
            row[0]
            for row in conn.execute(
                text(
                    "SELECT status FROM pipeline_runs WHERE filing_key=:fk AND stage='ingest'"
                    " ORDER BY id"
                ),
                {"fk": identity.filing_key},
            ).fetchall()
        ]
    assert "failed" in statuses, "the reason must be recorded on pipeline_runs"
    assert "completed" not in statuses


async def test_ingest_records_no_source_document_rows_when_nothing_downloaded(
    store, monkeypatch, tmp_path
):
    identity = FilingIdentity(stock_code=STOCK, year=2025, quarter="Q1")
    company_id = store.upsert_company(STOCK, name_zh="台積電")
    _no_downloads(monkeypatch, store, company_id)

    with pytest.raises(RuntimeError):
        await run_ingest_async(identity, store, tmp_path)

    filing_id = store.get_filing_id(identity.filing_key)
    with store.conn() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM source_documents WHERE filing_id=:fid"),
            {"fid": filing_id},
        ).scalar_one()
    assert count == 0

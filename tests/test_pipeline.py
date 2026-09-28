"""Pipeline stage behaviour that is not covered by the storage or API suites.

These tests never reach the network: the per-source download helpers in
src.pipeline.ingest are patched, which is also the only way to reproduce the
"every source returned nothing" case deterministically.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from src.domain.identity import FilingIdentity
from src.domain.models import Fact
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


async def test_insights_refuses_a_filing_with_no_source_document(store, monkeypatch, tmp_path):
    """Nothing behind the numbers means the filing must not present as ready."""
    from src.pipeline.build_insights import run_build_insights

    identity = FilingIdentity(stock_code=STOCK, year=2025, quarter="Q1")
    company_id = store.upsert_company(STOCK, name_zh="台積電")
    filing_id = store.upsert_filing(identity, company_id)
    store.update_filing_status(filing_id, "extracted")

    with pytest.raises(ValueError, match="no source document"):
        run_build_insights(identity, store)

    assert store.get_filing_status(identity.filing_key) != "insight_ready"


async def test_insights_demotes_a_filing_already_marked_ready_without_documents(
    store, monkeypatch, tmp_path
):
    """The ingest guard cannot fix filings the old code already advanced.

    7418_2026Q1 reached insight_ready with zero documents before the guard
    existed, so the invariant has to correct an existing violation rather than
    only prevent new ones.
    """
    from src.pipeline.build_insights import run_build_insights

    identity = FilingIdentity(stock_code=STOCK, year=2025, quarter="Q1")
    company_id = store.upsert_company(STOCK, name_zh="台積電")
    filing_id = store.upsert_filing(identity, company_id)
    store.update_filing_status(filing_id, "insight_ready")

    with pytest.raises(ValueError, match="demoted from insight_ready"):
        run_build_insights(identity, store)

    assert store.get_filing_status(identity.filing_key) == "extracted"


async def test_insights_also_demotes_from_validated(store, monkeypatch, tmp_path):
    """`validated` is consumer-ready too, and validate() sets it directly.

    build_envelope serves both `validated` and `insight_ready`, so demoting only
    from the latter would leave a document-less filing presenting as ready via a
    status that the validate stage assigns on its own.
    """
    from src.pipeline.build_insights import run_build_insights

    identity = FilingIdentity(stock_code=STOCK, year=2025, quarter="Q1")
    company_id = store.upsert_company(STOCK, name_zh="台積電")
    filing_id = store.upsert_filing(identity, company_id)
    store.update_filing_status(filing_id, "validated")

    with pytest.raises(ValueError, match="demoted from validated"):
        run_build_insights(identity, store)

    assert store.get_filing_status(identity.filing_key) == "extracted"


# ── the chain, not the links ──────────────────────────────────────────────────
#
# Nothing exercised extract → validate → insights as a whole. Every stage had
# unit coverage and the suite was green while the containerised extract produced
# zero chunks and reported success, and again while a re-validate left every
# filing one status below what the API serves. Both were found by hand against a
# live database. This runs the chain end to end.
#
# PDF parsing itself is stubbed: pdfplumber's own behaviour is covered in
# test_domain, and the failure it hid was a packaging problem (the extra missing
# from the image), which no in-process test can see. Everything downstream of
# page text is real -- section detection, chunking, storage, the rules, the
# score, and the status transitions.

_PAGES = [
    "合併資產負債表\n民國114年3月31日\n單位：新台幣仟元\n資產總計 57,578,493",
    "四、 重大會計政策之彙總說明\n本合併財務報告係依照證券發行人財務報告編製準則編製。",
    "十、 應收帳款\n應收帳款淨額如下，本公司依存續期間預期信用損失評估備抵損失。" * 6,
    "（十二）無形資產\n無形資產成本與累計攤銷明細如下，攤銷費用列入營業費用項下。" * 6,
]


@pytest.fixture
def staged_filing(store, tmp_path, monkeypatch):
    """A filing at `ingested` with a source document, ready for extract."""
    from src.parsers import pdf_text_parser
    from src.parsers.pdf_text_parser import PageText
    from src.pipeline import extract as extract_module

    identity = FilingIdentity(stock_code="3661", year=2025, quarter="Q1")
    company_id = store.upsert_company("3661", name_zh="世芯-KY")
    filing_id = store.upsert_filing(identity, company_id)

    pdf = tmp_path / "202501_3661_AI1.pdf"
    pdf.write_bytes(b"%PDF-1.4 stub")
    store.save_source_doc(filing_id, "pdf", pdf, None, pdf.stat().st_size)

    monkeypatch.setattr(
        pdf_text_parser,
        "extract_pages",
        lambda path: [
            PageText(page_number=i + 1, text=t, char_count=len(t), has_tables=False)
            for i, t in enumerate(_PAGES)
        ],
    )

    async def _no_finmind(identity, filing_id, store):
        return 0

    monkeypatch.setattr(extract_module, "_fetch_finmind_facts", _no_finmind)

    store.save_facts_bulk(
        filing_id,
        [
            Fact(filing_key=identity.filing_key, field=field, value=value, source_type="finmind")
            for field, value in [
                ("net_revenue", 10_484_855.0),
                ("gross_profit", 2_100_000.0),
                ("operating_income", 1_700_000.0),
                ("net_income", 1_461_343.0),
                ("total_assets", 57_578_493.0),
                ("total_liabilities", 15_971_430.0),
                ("equity", 41_607_063.0),
                ("operating_cash_flow", 900_000.0),
            ]
        ],
    )
    store.update_filing_status(filing_id, "ingested")
    return identity, filing_id, pdf


async def test_extract_validate_insights_runs_as_a_chain(store, staged_filing):
    """Each stage must leave the next one, and the API, something usable."""
    from src.pipeline.build_insights import run_build_insights
    from src.pipeline.extract import run_extract_async
    from src.pipeline.validate import run_validate

    identity, filing_id, pdf = staged_filing
    fk = identity.filing_key

    extract = await run_extract_async(identity, store, {"pdf_path": pdf}, force=True)
    assert extract["chunks_count"] > 0, "extract reported success having produced nothing"
    assert store.get_filing_status(fk) == "extracted"
    chunks = store.get_chunks(fk)
    assert chunks
    # The numbered notes must survive as their own titled sections.
    titles = {c["section_title"] for c in chunks}
    assert "應收帳款" in titles and "無形資產" in titles
    assert {c["section_type"] for c in chunks} & {"note"}

    run_validate(identity, store)
    assert store.get_filing_status(fk) == "validated"
    assert store.get_validation_results(fk)

    run_build_insights(identity, store)
    assert store.get_filing_status(fk) == "insight_ready"
    assert store.get_metrics(fk)


async def test_the_chain_leaves_the_filing_servable_by_the_api(store, staged_filing, database_url):
    """The status regression that 144 green tests missed.

    Re-running validate alone left every filing at `validated`; the chain must
    end somewhere build_envelope will actually serve.
    """
    from fastapi.testclient import TestClient

    from src.api.app import create_app
    from src.pipeline.build_insights import run_build_insights
    from src.pipeline.extract import run_extract_async
    from src.pipeline.validate import run_validate

    identity, filing_id, pdf = staged_filing
    await run_extract_async(identity, store, {"pdf_path": pdf}, force=True)
    run_validate(identity, store)
    run_build_insights(identity, store)

    with TestClient(create_app(database_url)) as client:
        response = client.get("/v1/filings/3661/2025Q1/context?evidence_limit=5")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence_chunks"]
    assert body["corpus_version"] is not None
    assert body["retrieval"]["state"] == "not_applicable"

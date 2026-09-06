"""V1 API contract and Financial_Agent compatibility tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import text

from src.api.app import create_app
from src.domain.identity import FilingIdentity
from src.domain.models import Fact, InsightCard


class ConsumerIdentity(BaseModel):
    stock_code: str
    period: str
    company_name: str


class ConsumerFreshness(BaseModel):
    updated_at: datetime | None
    is_stale: bool


class ConsumerValidationFailure(BaseModel):
    rule_name: str
    passed: bool
    severity: str
    message: str | None
    checked_at: datetime | None


class ConsumerQuality(BaseModel):
    score: float | None
    missing_fields: list[str]
    validation_failures: list[ConsumerValidationFailure]


class ConsumerEvidence(BaseModel):
    source_type: str
    field: str | None
    page_number: int | None
    section_title: str | None
    excerpt: str | None
    confidence: float | None


class ConsumerSnapshotRecord(BaseModel):
    schema_version: str
    identity: ConsumerIdentity
    status: Literal["ready", "processing", "stale"]
    freshness: ConsumerFreshness
    quality: ConsumerQuality
    snapshot: dict[str, Any]
    metrics: dict[str, Any]
    events: list[dict[str, Any]]
    evidence: list[ConsumerEvidence]


@pytest.fixture
def api_client(database_url):
    app = create_app(database_url)
    with TestClient(app) as client:
        store = client.app.state.store
        identity = FilingIdentity(stock_code="2330", year=2025, quarter="Q1")
        company_id = store.upsert_company(
            "2330", name_zh="台積電", name_en="TSMC", industry="半導體", market="上市"
        )
        filing_id = store.upsert_filing(identity, company_id)
        store.save_facts_bulk(
            filing_id,
            [
                Fact(
                    filing_key=identity.filing_key,
                    field="net_revenue",
                    value=100_000,
                    source_type="xbrl",
                    xbrl_tag="Revenue",
                ),
                Fact(
                    filing_key=identity.filing_key,
                    field="eps_basic",
                    value=12.5,
                    unit="TWD_per_share",
                    source_type="xbrl",
                    xbrl_tag="BasicEarningsLossPerShare",
                ),
            ],
        )
        store.save_metric(filing_id, "gross_margin", 0.53, formula="gross_profit/net_revenue")
        store.save_validation_result(
            filing_id, "balance_sheet_equation", False, "error", "missing balance fields"
        )
        store.save_event(
            filing_id,
            "revenue_growth_acceleration",
            "info",
            "Revenue growth",
            "Revenue accelerated",
            related_fields=["net_revenue"],
        )
        store.save_insight_card(
            filing_id,
            InsightCard(
                filing_key=identity.filing_key,
                card_type="performance_summary",
                title="Performance",
                summary="Stable",
            ),
        )
        doc_id = store.save_source_doc(
            filing_id,
            "xbrl",
            None,
            url="https://example.test/report.xml",
            file_size=1234,
        )
        fact_id = store.get_filing_id(identity.filing_key)
        with store.conn() as conn:
            actual_fact_id = conn.execute(
                text(
                    "SELECT id FROM financial_facts WHERE filing_id=:filing_id"
                    " AND field='net_revenue'"
                ),
                {"filing_id": filing_id},
            ).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO fact_evidence"
                    "(fact_id,doc_id,page_number,section_title,raw_text,extraction_method)"
                    " VALUES(:fact_id,:doc_id,1,'Income statement','Revenue 100000','xbrl')"
                ),
                {"fact_id": actual_fact_id, "doc_id": doc_id},
            )
            conn.execute(
                text(
                    "UPDATE filings SET status='validated', quality_score=0.81,"
                    " updated_at=now() WHERE id=:filing_id"
                ),
                {"filing_id": filing_id},
            )
        assert fact_id == filing_id
        yield client


def test_snapshot_parses_with_consumer_equivalent_models(api_client) -> None:
    response = api_client.get("/v1/filings/2330/2025Q1/snapshot")
    assert response.status_code == 200

    record = ConsumerSnapshotRecord.model_validate(response.json())
    assert record.identity.company_name == "台積電"
    assert record.identity.period == "2025Q1"
    assert record.snapshot["eps"] == record.snapshot["eps_basic"] == 12.5
    assert record.metrics["gross_margin"] == pytest.approx(0.53)
    assert record.evidence[0].excerpt == "Revenue 100000"
    assert record.evidence[0].confidence == 1.0
    assert record.quality.validation_failures[0].rule_name == "balance_sheet_equation"
    assert record.quality.validation_failures[0].passed is False


def test_stock_and_period_compatibility_keys(api_client) -> None:
    stocks = api_client.get("/v1/stocks").json()
    periods = api_client.get("/v1/stocks/2330/periods").json()
    assert stocks["stocks"][0]["stock_code"] == "2330"
    assert stocks["stocks"] == stocks["items"]
    assert periods["periods"] == ["2025Q1"]
    assert periods["items"][0]["period"] == "2025Q1"


def test_full_fact_provenance_and_availability(api_client) -> None:
    data = api_client.get("/v1/filings/2330/2025Q1/context?evidence_limit=0").json()
    fact = next(item for item in data["facts"] if item["field"] == "net_revenue")
    assert fact["unit"] == "TWD_thousands"
    assert fact["source_type"] == "xbrl"
    assert fact["evidence"][0]["source_url"] == "https://example.test/report.xml"
    bank_field = next(
        item for item in data["field_availability"] if item["field"] == "net_interest_income"
    )
    assert bank_field["state"] == "not_applicable"
    assert "net_interest_income" not in data["quality"]["missing_fields"]


def test_not_ready_and_provider_failure_are_not_200(api_client) -> None:
    store = api_client.app.state.store
    filing_id = store.get_filing_id("2330_2025Q1")
    store.update_filing_status(filing_id, "ingested")
    response = api_client.get("/v1/filings/2330/2025Q1/snapshot")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "filing_not_ready"

    store.update_filing_status(filing_id, "failed")
    response = api_client.get("/v1/filings/2330/2025Q1/snapshot")
    assert response.status_code == 503
    assert response.json()["error"]["data_state"] == "provider_failure"


def test_error_mapping_filters_pagination_and_batch_bounds(api_client) -> None:
    assert api_client.get("/v1/filings/9999/2025Q1/snapshot").status_code == 404
    assert api_client.get("/v1/stocks?limit=0").status_code == 422
    unknown = api_client.get("/v1/filings/2330/2025Q1/snapshot?fields=unknown")
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "unknown_fields"

    oversized = {"items": [{"stock_code": "2330", "period": "2025Q1"} for _ in range(101)]}
    assert api_client.post("/v1/batch/filings/query", json=oversized).status_code == 422


def test_batch_returns_per_item_data_and_missing_error(api_client) -> None:
    response = api_client.post(
        "/v1/batch/filings/query",
        json={
            "items": [
                {"stock_code": "2330", "period": "2025Q1", "fields": ["eps_basic"]},
                {"stock_code": "9999", "period": "2025Q1"},
            ]
        },
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["data"]["snapshot"]["eps"] == 12.5
    assert items[0]["data"]["facts"][0]["field"] == "eps_basic"
    assert items[1]["error"]["code"] == "filing_not_found"


def test_discovery_defines_units_and_all_absence_states(api_client) -> None:
    assert api_client.get("/health/live").json()["status"] == "ok"
    assert api_client.get("/health/ready").json()["status"] == "ready"
    capabilities = api_client.get("/v1/capabilities").json()
    assert capabilities["units"]["ratio"].startswith("decimal-scaled")
    assert capabilities["units"]["percent"].startswith("100-scaled")
    assert set(capabilities["data_states"]) == {
        "present",
        "missing",
        "null",
        "not_applicable",
        "provider_failure",
    }
    assert any(field["name"] == "net_interest_income" for field in capabilities["fields"])


def test_openapi_is_consumer_contract_baseline(api_client) -> None:
    schema = api_client.get("/openapi.json").json()
    required_paths = {
        "/v1/filings/{stock_code}/{period}/snapshot",
        "/v1/filings/{stock_code}/{period}/context",
        "/v1/stocks/{stock_code}/periods",
        "/v1/stocks",
        "/v1/filings/{stock_code}/{period}/refresh",
        "/v1/jobs/{job_id}",
    }
    assert required_paths <= set(schema["paths"])
    envelope = schema["components"]["schemas"]["FilingEnvelope"]
    assert {
        "identity",
        "status",
        "freshness",
        "quality",
        "snapshot",
        "metrics",
        "events",
        "evidence",
    } <= set(envelope["required"])
    assert envelope["properties"]["metrics"]["type"] == "object"


def test_committed_openapi_matches_application(api_client) -> None:
    committed = json.loads(Path("docs/openapi-v1.json").read_text(encoding="utf-8"))
    assert committed == api_client.app.openapi()


def test_refresh_and_job_contract(api_client) -> None:
    async def successful_refresh(identity, store, output_dir):
        return {"validate": {"status": "completed"}}

    api_client.app.state.refresh_runner = successful_refresh
    response = api_client.post("/v1/filings/2330/2025Q1/refresh")
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    job = api_client.get(f"/v1/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] == "succeeded"


def test_a_filing_with_no_source_documents_is_a_conflict_not_an_outage(api_client):
    """503 told the consumer the whole producer was down.

    A filing that never obtained a source document fails its pipeline by
    design, but the provider-failure branch reported that as 503 retryable --
    so a client backing off surfaced "FinancialReports is unavailable" for one
    permanently empty filing, and a real outage became indistinguishable from
    it. It is a conflict with the filing's own state and it will not resolve.
    """
    store = api_client.app.state.store
    filing_id = store.get_filing_id("2330_2025Q1")
    with store.conn() as conn:
        for table in ("document_chunks", "document_sections", "document_pages"):
            conn.execute(
                text(
                    f"DELETE FROM {table} WHERE doc_id IN"
                    " (SELECT id FROM source_documents WHERE filing_id=:fid)"
                ),
                {"fid": filing_id},
            )
        conn.execute(
            text(
                "DELETE FROM fact_evidence WHERE doc_id IN"
                " (SELECT id FROM source_documents WHERE filing_id=:fid)"
            ),
            {"fid": filing_id},
        )
        conn.execute(text("DELETE FROM source_documents WHERE filing_id=:fid"), {"fid": filing_id})

    response = api_client.get("/v1/filings/2330/2025Q1/snapshot")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "filing_has_no_source_documents"
    assert error["retryable"] is False


def test_a_failed_refresh_job_does_not_echo_third_party_error_text(api_client):
    """A job error is consumer-facing, so it must not carry internals.

    This path used to do both things an error path must not: it logged nothing,
    so the cause existed nowhere, and it put str(exc) straight into the job. A
    driver error carries the connection URL, credentials included.
    """

    async def _boom(identity, store, output_dir):
        raise OSError("could not connect to postgresql+psycopg://user:secret@db:5432/financial")

    api_client.app.state.refresh_runner = _boom

    created = api_client.post("/v1/filings/2330/2025Q1/refresh")
    assert created.status_code == 202
    job = api_client.get(f"/v1/jobs/{created.json()['job_id']}").json()

    assert job["status"] == "failed"
    assert "secret" not in job["error"]
    assert "db:5432" not in job["error"]
    assert "OSError" in job["error"], "the type is still useful for diagnosis"


def test_a_deliberate_pipeline_error_stays_readable_in_the_job(api_client):
    """Messages this project writes are meant to be read; don't redact those."""

    async def _boom(identity, store, output_dir):
        raise RuntimeError("no source document could be obtained for 2330_2025Q1")

    api_client.app.state.refresh_runner = _boom

    created = api_client.post("/v1/filings/2330/2025Q1/refresh")
    job = api_client.get(f"/v1/jobs/{created.json()['job_id']}").json()

    assert job["status"] == "failed"
    assert "no source document could be obtained for 2330_2025Q1" in job["error"]


def test_an_unhandled_error_keeps_the_documented_error_shape(database_url):
    """A 500 used to return FastAPI's {"detail": ...}, which no consumer parses."""
    app = create_app(database_url)

    @app.get("/v1/_boom")
    async def _boom() -> None:
        raise KeyError("internal detail /app/secret/path")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/v1/_boom")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["retryable"] is True
    assert "secret" not in response.text

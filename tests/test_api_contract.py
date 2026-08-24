"""V1 API contract and Financial_Agent compatibility tests."""

from __future__ import annotations

from datetime import datetime
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
def api_client(tmp_path):
    app = create_app(tmp_path / "api.db")
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
                    " updated_at=datetime('now') WHERE id=:filing_id"
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

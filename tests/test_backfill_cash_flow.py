"""backfill-cash-flow-quarter: offline, FinMind served by a mock transport."""

from __future__ import annotations

import httpx
import pytest
from sqlalchemy import text

from src.domain.identity import FilingIdentity
from src.domain.models import Fact
from src.pipeline.backfill_cash_flow import backfill_cash_flow_quarter
from src.storage.store import FilingStore


@pytest.fixture
def store(database_url):
    return FilingStore(database_url)


def _transport(rows_by_stock: dict[str, list[tuple[str, float]]]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        rows = rows_by_stock.get(request.url.params["data_id"], [])
        data = [
            {"date": d, "type": "CashFlowsFromOperatingActivities", "value": v} for d, v in rows
        ]
        return httpx.Response(200, json={"status": 200, "data": data})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _seed(store: FilingStore, stock: str, quarter: str, market: str = "上市") -> int:
    identity = FilingIdentity(stock, 2026, quarter)
    filing_id = store.upsert_filing(identity, store.upsert_company(stock, "測試", market=market))
    store.save_facts_bulk(
        filing_id,
        [
            Fact(filing_key=identity.filing_key, field=name, value=value, source_type="finmind")
            for name, value in [("net_income", 1000.0), ("operating_cash_flow", 2100.0)]
        ],
    )
    # What the old code left behind: a YTD-over-quarter ratio and a card quoting it.
    store.save_metric(filing_id, "cf_quality", 2.1)
    store.save_metric(filing_id, "net_margin", 0.5)
    with store.conn() as c:
        c.execute(
            text(
                "INSERT INTO insight_cards(filing_id, card_type, title, summary)"
                " VALUES(:f, 'cash_flow_quality', 't', 'stale')"
            ),
            {"f": filing_id},
        )
    store.update_filing_status(filing_id, "insight_ready")
    return filing_id


def _counts(store: FilingStore, filing_id: int) -> dict[str, int]:
    with store.conn() as c:
        return {
            t: c.execute(
                text(f"SELECT COUNT(*) FROM {t} WHERE filing_id=:f"), {"f": filing_id}
            ).scalar_one()
            for t in ("financial_facts", "financial_metrics", "insight_cards")
        }


async def test_dry_run_reports_and_writes_nothing(store):
    filing_id = _seed(store, "2330", "Q2")
    before = _counts(store, filing_id)
    async with _transport(
        {"2330": [("2026-03-31", 700_000.0), ("2026-06-30", 2_100_000.0)]}
    ) as http:
        summary = await backfill_cash_flow_quarter(store, dry_run=True, delay=0, client=http)

    (outcome,) = summary.outcomes
    assert outcome.status == "added"
    assert outcome.value == 1400.0
    assert (outcome.cf_quality_before, outcome.cf_quality_after) == (2.1, 1.4)
    assert _counts(store, filing_id) == before
    assert store.get_facts("2330_2026Q2", ["operating_cash_flow_quarter"]) == []


async def test_real_run_adds_the_fact_and_replaces_the_analytics(store):
    filing_id = _seed(store, "2330", "Q2")
    async with _transport(
        {"2330": [("2026-03-31", 700_000.0), ("2026-06-30", 2_100_000.0)]}
    ) as http:
        await backfill_cash_flow_quarter(store, delay=0, client=http)

    (fact,) = store.get_facts("2330_2026Q2", ["operating_cash_flow_quarter"])
    assert fact["value"] == 1400.0
    assert (fact["period_start"], fact["period_end"]) == ("2026-04-01", "2026-06-30")
    metrics = {m["metric_name"]: m["value"] for m in store.get_metrics("2330_2026Q2")}
    assert metrics["cf_quality"] == 1.4
    with store.conn() as c:
        summaries = [
            r[0]
            for r in c.execute(
                text("SELECT summary FROM insight_cards WHERE filing_id=:f"), {"f": filing_id}
            )
        ]
    assert "stale" not in summaries  # old cards replaced, not appended to


async def test_second_run_changes_nothing(store):
    filing_id = _seed(store, "2330", "Q2")
    rows = {"2330": [("2026-03-31", 700_000.0), ("2026-06-30", 2_100_000.0)]}
    async with _transport(rows) as http:
        await backfill_cash_flow_quarter(store, delay=0, client=http)
        after_first = _counts(store, filing_id)
        again = await backfill_cash_flow_quarter(store, delay=0, client=http)

    assert [o.status for o in again.outcomes] == ["unchanged"]
    assert _counts(store, filing_id) == after_first


async def test_missing_previous_quarter_gives_no_fact_and_drops_the_stale_ratio(store):
    filing_id = _seed(store, "2330", "Q2")
    async with _transport({"2330": [("2026-06-30", 2_100_000.0)]}) as http:
        summary = await backfill_cash_flow_quarter(store, delay=0, client=http)

    assert [o.status for o in summary.outcomes] == ["no_previous_row"]
    assert store.get_facts("2330_2026Q2", ["operating_cash_flow_quarter"]) == []
    assert "cf_quality" not in {m["metric_name"] for m in store.get_metrics("2330_2026Q2")}
    assert _counts(store, filing_id)["financial_metrics"] > 0


async def test_no_cash_flow_row_is_reported_separately(store):
    _seed(store, "2330", "Q3")
    async with _transport({}) as http:
        summary = await backfill_cash_flow_quarter(store, delay=0, client=http)
    assert [o.status for o in summary.outcomes] == ["no_current_row"]


async def test_emerging_board_second_quarter_takes_the_ytd_value(store):
    _seed(store, "7418", "Q2", market="興櫃")
    async with _transport({"7418": [("2026-06-30", 90_000.0)]}) as http:
        await backfill_cash_flow_quarter(store, delay=0, client=http)

    (fact,) = store.get_facts("7418_2026Q2", ["operating_cash_flow_quarter"])
    assert fact["value"] == 90.0
    assert fact["period_start"] == "2026-01-01"


async def test_stock_filter_leaves_other_filings_alone(store):
    _seed(store, "2330", "Q2")
    other = _seed(store, "2317", "Q2")
    async with _transport({"2330": [("2026-03-31", 1.0), ("2026-06-30", 2.0)]}) as http:
        summary = await backfill_cash_flow_quarter(store, stock="2330", delay=0, client=http)

    assert [o.filing_key for o in summary.outcomes] == ["2330_2026Q2"]
    assert store.get_facts("2317_2026Q2", ["operating_cash_flow_quarter"]) == []
    assert _counts(store, other)["insight_cards"] == 1


def test_command_dry_run_prints_the_table(store, database_url, monkeypatch):
    from typer.testing import CliRunner

    from src import cli
    from src.pipeline import backfill_cash_flow as module

    _seed(store, "2330", "Q2")
    transport = _transport({"2330": [("2026-03-31", 700_000.0), ("2026-06-30", 2_100_000.0)]})
    original = module.backfill_cash_flow_quarter

    async def with_mock(store, **kwargs):
        return await original(store, client=transport, delay=0, **kwargs)

    monkeypatch.setattr(module, "backfill_cash_flow_quarter", with_mock)
    result = CliRunner().invoke(
        cli.app,
        ["backfill-cash-flow-quarter", "--dry-run", "--db", database_url, "--show", "2330_2026Q2"],
    )

    assert result.exit_code == 0, result.output
    assert "Would write" in result.output and "2330_2026Q2" in result.output
    assert store.get_facts("2330_2026Q2", ["operating_cash_flow_quarter"]) == []

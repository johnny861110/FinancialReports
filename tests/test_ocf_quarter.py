"""operating_cash_flow_quarter: cash flow over the income statement's months.

FinMind's cash-flow dataset is year-to-date; the derived fact subtracts the
previous quarter-end row of the same response. Offline throughout.
"""

from __future__ import annotations

import httpx
import pytest

from src.analytics.comparisons import YTD_CASHFLOW_FIELDS, compute_changes
from src.analytics.insight_builder import build_cash_flow_insight
from src.analytics.metrics import compute_all_metrics
from src.domain.identity import FilingIdentity
from src.normalize.period_normalizer import finmind_period_start
from src.sources.finmind_client import FinMindClient, operating_cash_flow_quarter

# YTD operating cash flow in full TWD; FinMind dates each row by quarter-end.
YTD = {
    "03-31": 100_000_000.0,
    "06-30": 250_000_000.0,
    "09-30": 330_000_000.0,
    "12-31": 500_000_000.0,
}


def _records(*dates: str, kind: str = "CashFlowsFromOperatingActivities") -> list[dict]:
    return [{"date": f"2026-{d}", "type": kind, "value": YTD[d]} for d in dates]


def _identity(quarter: str) -> FilingIdentity:
    return FilingIdentity(stock_code="2330", year=2026, quarter=quarter)


@pytest.mark.parametrize(
    ("quarter", "expected"),
    [("Q1", 100_000.0), ("Q2", 150_000.0), ("Q3", 80_000.0), ("Q4", 170_000.0)],
)
def test_single_quarter_is_ytd_less_previous_quarter_end(quarter, expected):
    assert operating_cash_flow_quarter(_records(*YTD), _identity(quarter)) == expected


@pytest.mark.parametrize("quarter", ["Q2", "Q3", "Q4"])
def test_missing_previous_row_gives_no_value(quarter):
    current = {"Q2": "06-30", "Q3": "09-30", "Q4": "12-31"}[quarter]
    assert operating_cash_flow_quarter(_records(current), _identity(quarter)) is None


def test_missing_current_row_gives_no_value():
    assert operating_cash_flow_quarter(_records("03-31"), _identity("Q2")) is None


def test_semiannual_second_quarter_is_the_ytd_value():
    assert (
        operating_cash_flow_quarter(_records("06-30"), _identity("Q2"), semiannual=True)
        == 250_000.0
    )


def test_alias_type_is_read_too():
    records = _records("03-31", "06-30", kind="NetCashInflowFromOperatingActivities")
    assert operating_cash_flow_quarter(records, _identity("Q2")) == 150_000.0


def test_derived_fact_starts_where_an_income_fact_does():
    assert str(finmind_period_start(_identity("Q2"), "operating_cash_flow_quarter")) == "2026-04-01"
    assert str(finmind_period_start(_identity("Q2"), "operating_cash_flow")) == "2026-01-01"
    assert (
        str(finmind_period_start(_identity("Q2"), "operating_cash_flow_quarter", semiannual=True))
        == "2026-01-01"
    )


async def test_fetch_facts_emits_the_derived_fact_beside_the_stored_ones():
    cash_flow = _records("03-31", "06-30")

    def handler(request: httpx.Request) -> httpx.Response:
        dataset = request.url.params["dataset"]
        data = cash_flow if dataset == "TaiwanStockCashFlowsStatement" else []
        return httpx.Response(200, json={"status": 200, "data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        facts = await FinMindClient().fetch_facts_async(_identity("Q2"), client=http)

    by_field = {f["field"]: f for f in facts}
    assert by_field["operating_cash_flow"]["value"] == 250_000.0  # still the YTD value
    assert by_field["operating_cash_flow_quarter"]["value"] == 150_000.0
    assert by_field["operating_cash_flow_quarter"]["period_type"] == "duration"


# ── cf_quality, QoQ and the insight card use the same-period value ───────────

# 2330 2026Q2, thousands of TWD
Q2 = {
    "net_income": 706_780_923.0,
    "operating_cash_flow": 1_482_341_242.0,  # year-to-date
    "operating_cash_flow_quarter": 783_364_977.0,
}


def test_cf_quality_divides_the_quarter_value_by_net_income():
    assert compute_all_metrics(Q2)["cf_quality"] == round(783_364_977 / 706_780_923, 4)


def test_cf_quality_is_absent_without_the_derived_fact():
    facts = {k: v for k, v in Q2.items() if k != "operating_cash_flow_quarter"}
    assert "cf_quality" not in compute_all_metrics(facts)


def test_cash_flow_card_still_builds_without_cf_quality():
    facts = {k: v for k, v in Q2.items() if k != "operating_cash_flow_quarter"}
    card = build_cash_flow_insight(_identity("Q2"), facts, compute_all_metrics(facts))
    assert card is not None
    assert "現金流品質比" not in card["summary"]
    assert card["data_points"]["cf_quality_ratio"] is None


def test_qoq_compares_the_quarter_field_and_skips_ytd_cash_flow():
    q1 = {"operating_cash_flow": 698_976_265.0, "operating_cash_flow_quarter": 698_976_265.0}
    changes = {c["field"]: c for c in compute_changes(Q2, q1, exclude=YTD_CASHFLOW_FIELDS)}
    assert "operating_cash_flow" not in changes
    assert round(changes["operating_cash_flow_quarter"]["change_pct"], 1) == 12.1


def test_yoy_still_compares_ytd_cash_flow():
    assert "operating_cash_flow" in {c["field"] for c in compute_changes(Q2, Q2)}


def test_ytd_set_keeps_balance_like_and_derived_fields_out():
    assert {"operating_cash_flow", "investing_cash_flow", "capex"} <= YTD_CASHFLOW_FIELDS
    assert not YTD_CASHFLOW_FIELDS & {"operating_cash_flow_quarter", "cash_ending"}

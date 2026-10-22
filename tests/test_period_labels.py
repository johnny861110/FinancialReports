"""period_start on FinMind duration facts.

FinMind's income-statement dataset returns the quarter on its own while its
cash-flow dataset returns year-to-date; both used to be labelled Jan 1.
Offline: FinMindClient.fetch_facts_async is replaced.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.domain.identity import FilingIdentity
from src.normalize.period_normalizer import finmind_period_start, quarter_start
from src.pipeline import extract as extract_module
from src.sources import finmind_client
from src.storage.store import FilingStore


@pytest.fixture
def store(database_url):
    return FilingStore(database_url)


def _identity(quarter: str, stock: str = "2330") -> FilingIdentity:
    return FilingIdentity(stock_code=stock, year=2026, quarter=quarter)


def _raw(field: str, period_type: str = "duration") -> dict:
    return {
        "field": field,
        "value": 1.0,
        "unit": "TWD_thousands",
        "period_type": period_type,
        "confidence": 0.95,
        "xbrl_tag": field,
    }


@pytest.mark.parametrize(
    ("quarter", "start"),
    [
        ("Q1", date(2026, 1, 1)),
        ("Q2", date(2026, 4, 1)),
        ("Q3", date(2026, 7, 1)),
        ("Q4", date(2026, 10, 1)),
    ],
)
def test_quarter_start_is_the_first_day_of_the_quarter(quarter, start):
    assert quarter_start(_identity(quarter)) == start


@pytest.mark.parametrize(
    ("quarter", "start"),
    [
        ("Q1", date(2026, 1, 1)),
        ("Q2", date(2026, 4, 1)),
        ("Q3", date(2026, 7, 1)),
        ("Q4", date(2026, 10, 1)),
    ],
)
def test_income_statement_fields_start_at_the_quarter(quarter, start):
    for field in ("net_income", "eps_basic", "net_revenue"):
        assert finmind_period_start(_identity(quarter), field) == start


@pytest.mark.parametrize("quarter", ["Q1", "Q2", "Q3", "Q4"])
def test_cash_flow_fields_are_year_to_date(quarter):
    for field in ("operating_cash_flow", "investing_cash_flow", "capex"):
        assert finmind_period_start(_identity(quarter), field) == date(2026, 1, 1)


def test_semiannual_filer_second_quarter_covers_the_half_year():
    assert finmind_period_start(_identity("Q2"), "eps_basic", semiannual=True) == date(2026, 1, 1)


def _save(store: FilingStore, identity: FilingIdentity, market: str | None, monkeypatch, raw):
    company_id = store.upsert_company(identity.stock_code, "測試", market=market)
    filing_id = store.upsert_filing(identity, company_id)

    async def _fake(self, ident, client=None):
        return raw

    monkeypatch.setattr(finmind_client.FinMindClient, "fetch_facts_async", _fake)
    return filing_id


async def _labels(store, identity, market, monkeypatch, raw) -> dict[str, tuple[str, str]]:
    filing_id = _save(store, identity, market, monkeypatch, raw)
    await extract_module._fetch_finmind_facts(identity, filing_id, store)
    return {
        f["field"]: (f["period_start"], f["period_end"])
        for f in store.get_facts(identity.filing_key)
    }


FIELDS = [_raw("net_income"), _raw("operating_cash_flow"), _raw("total_assets", "instant")]


@pytest.mark.parametrize(
    ("quarter", "income_start", "end"),
    [
        ("Q2", "2026-04-01", "2026-06-30"),
        ("Q3", "2026-07-01", "2026-09-30"),
        ("Q4", "2026-10-01", "2026-12-31"),
    ],
)
async def test_quarterly_filer_labels(store, monkeypatch, quarter, income_start, end):
    labels = await _labels(store, _identity(quarter), "上市", monkeypatch, FIELDS)
    assert labels["net_income"] == (income_start, end)
    assert labels["operating_cash_flow"] == ("2026-01-01", end)
    assert labels["total_assets"] == (end, end)


async def test_first_quarter_is_unchanged(store, monkeypatch):
    labels = await _labels(store, _identity("Q1"), "上市", monkeypatch, FIELDS)
    assert labels["net_income"] == ("2026-01-01", "2026-03-31")
    assert labels["operating_cash_flow"] == ("2026-01-01", "2026-03-31")


async def test_emerging_board_second_quarter_is_the_half_year(store, monkeypatch):
    labels = await _labels(store, _identity("Q2", "7418"), "興櫃", monkeypatch, FIELDS)
    assert labels["net_income"] == ("2026-01-01", "2026-06-30")
    assert labels["operating_cash_flow"] == ("2026-01-01", "2026-06-30")


async def test_unknown_market_is_treated_as_a_quarterly_filer(store, monkeypatch):
    labels = await _labels(store, _identity("Q2"), None, monkeypatch, FIELDS)
    assert labels["net_income"] == ("2026-04-01", "2026-06-30")

"""Company name / industry / market resolution, with the exchange APIs mocked."""

from __future__ import annotations

import pytest

from src.normalize.company_mapper import backfill_companies, resolve_company
from src.sources import mops_client
from src.sources.mops_client import MOPSClient
from src.storage.store import FilingStore

TWSE_ROWS = [
    {"公司代號": "2330", "公司簡稱": "台積電", "產業別": "24"},
    {"公司代號": "2317", "公司簡稱": "鴻海", "產業別": "99"},
]
TPEX_ROWS = [
    {
        "SecuritiesCompanyCode": "1240",
        "CompanyAbbreviation": "茂生農經",
        "SecuritiesIndustryCode": "33",
    },
]
EMERGING_ROWS = [
    {
        "SecuritiesCompanyCode": "7418",
        "CompanyAbbreviation": "香繼光",
        "SecuritiesIndustryCode": "16",
    },
    # Also on the TWSE list: it moved up a board, so the listed entry must win.
    {
        "SecuritiesCompanyCode": "2330",
        "CompanyAbbreviation": "舊名",
        "SecuritiesIndustryCode": "01",
    },
]


class _Response:
    def __init__(self, payload, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _client(monkeypatch, responses: dict[str, object]) -> MOPSClient:
    """A client whose HTTP layer serves `responses` by URL substring."""
    monkeypatch.setattr(mops_client, "_DIRECTORY_CACHE", None)
    client = MOPSClient()

    def fake_get(url: str, **_kwargs):
        for fragment, payload in responses.items():
            if fragment in url:
                if isinstance(payload, Exception):
                    raise payload
                return _Response(payload)
        raise AssertionError(f"unexpected request to {url}")

    monkeypatch.setattr(client._session, "get", fake_get)
    return client


@pytest.fixture
def working_client(monkeypatch) -> MOPSClient:
    return _client(
        monkeypatch,
        {"twse.com.tw": TWSE_ROWS, "t187ap03_O": TPEX_ROWS, "t187ap03_R": EMERGING_ROWS},
    )


@pytest.fixture
def store(database_url):
    return FilingStore(database_url)


def _row(store: FilingStore, code: str) -> tuple:
    from sqlalchemy import text

    with store.conn() as c:
        return tuple(
            c.execute(
                text("SELECT name_zh, industry, market FROM companies WHERE stock_code=:sc"),
                {"sc": code},
            ).fetchone()
        )


def test_directory_parsing_maps_both_exchanges(working_client) -> None:
    assert working_client.get_company_info("2330") == {
        "name_zh": "台積電",
        "industry": "半導體業",
        "market": "上市",
    }
    assert working_client.get_company_info("1240") == {
        "name_zh": "茂生農經",
        "industry": "農業科技業",
        "market": "上櫃",
    }


def test_unknown_industry_code_is_kept_verbatim(working_client) -> None:
    assert working_client.get_company_info("2317")["industry"] == "99"


def test_unlisted_code_gives_nulls_not_the_stock_code(working_client) -> None:
    assert working_client.get_company_info("9999") == {
        "name_zh": None,
        "industry": None,
        "market": None,
    }


def test_api_failure_gives_nulls_warns_and_is_retried(monkeypatch, caplog) -> None:
    client = _client(monkeypatch, {"twse.com.tw": OSError("boom")})

    with caplog.at_level("WARNING"):
        assert client.get_company_info("2330")["name_zh"] is None
    assert "Company directory fetch failed" in caplog.text

    # The failure must not be cached: a later lookup succeeds once the API is back.
    client = _client(
        monkeypatch,
        {"twse.com.tw": TWSE_ROWS, "t187ap03_O": TPEX_ROWS, "t187ap03_R": EMERGING_ROWS},
    )
    assert client.get_company_info("2330")["name_zh"] == "台積電"


def test_new_company_with_failed_lookup_stores_null(monkeypatch, store) -> None:
    client = _client(monkeypatch, {"twse.com.tw": OSError("boom")})

    company_id, name = resolve_company("2330", store, client)

    assert isinstance(company_id, int)
    assert name == "2330"  # display fallback only
    assert _row(store, "2330") == (None, None, None)


def test_placeholder_row_is_requeried_and_overwritten(working_client, store) -> None:
    store.upsert_company("2330", name_zh="2330")

    _, name = resolve_company("2330", store, working_client)

    assert name == "台積電"
    assert _row(store, "2330") == ("台積電", "半導體業", "上市")


def test_null_name_row_is_requeried(working_client, store) -> None:
    store.upsert_company("2330")

    resolve_company("2330", store, working_client)

    assert _row(store, "2330") == ("台積電", "半導體業", "上市")


def test_real_name_is_not_requeried(monkeypatch, store) -> None:
    store.upsert_company("2330", name_zh="台積電")
    client = _client(monkeypatch, {})  # any request raises

    assert resolve_company("2330", store, client)[1] == "台積電"


def test_backfill_is_idempotent(working_client, store) -> None:
    store.upsert_company("2330", name_zh="2330")
    store.upsert_company("9999", name_zh="9999")
    store.upsert_company("1240", name_zh="自訂名稱")

    first = backfill_companies(store, working_client)
    second = backfill_companies(store, working_client)

    assert {code for code, _, _ in first} == {"2330", "9999", "1240"}
    assert second == []
    assert _row(store, "2330") == ("台積電", "半導體業", "上市")
    assert _row(store, "9999") == (None, None, None)


def test_backfill_dry_run_writes_nothing(working_client, store) -> None:
    store.upsert_company("2330", name_zh="2330")

    assert backfill_companies(store, working_client, dry_run=True)
    assert _row(store, "2330") == ("2330", None, None)


def test_backfill_keeps_real_data_when_directory_is_down(monkeypatch, store) -> None:
    store.upsert_company("2330", name_zh="台積電", industry="半導體業", market="上市")
    client = _client(monkeypatch, {"twse.com.tw": OSError("boom")})

    assert backfill_companies(store, client) == []
    assert _row(store, "2330") == ("台積電", "半導體業", "上市")


def test_emerging_board_company_is_resolved(working_client) -> None:
    assert working_client.get_company_info("7418") == {
        "name_zh": "香繼光",
        "industry": "觀光餐旅",
        "market": "興櫃",
    }


def test_a_company_on_a_higher_board_keeps_that_listing(working_client) -> None:
    assert working_client.get_company_info("2330") == {
        "name_zh": "台積電",
        "industry": "半導體業",
        "market": "上市",
    }


def test_the_emerging_list_failing_still_returns_the_partial_directory_uncached(
    monkeypatch, caplog
) -> None:
    client = _client(
        monkeypatch,
        {"twse.com.tw": TWSE_ROWS, "t187ap03_O": TPEX_ROWS, "t187ap03_R": OSError("boom")},
    )

    with caplog.at_level("WARNING"):
        assert client.get_company_info("2330")["name_zh"] == "台積電"
        assert client.get_company_info("7418")["name_zh"] is None
    assert "Company directory fetch failed" in caplog.text
    assert mops_client._DIRECTORY_CACHE is None

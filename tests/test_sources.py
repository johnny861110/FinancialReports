"""Boundary tests for source clients and their typed adapters."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from src.domain.identity import FilingIdentity
from src.sources.finmind_client import FinMindClient
from src.sources.mops_client import MOPSClient
from src.sources.pdf_client import MOPSPDFClient
from src.sources.xbrl_client import XBRLClient


def test_mops_company_parser_ignores_non_table_nodes() -> None:
    html = """
    <html><body><table><tr><td>公司名稱</td><td>台灣積體電路</td></tr></table></body></html>
    """

    assert MOPSClient()._parse_company_info(html) == {"name_zh": "台灣積體電路"}


@pytest.mark.asyncio
async def test_xbrl_external_client_remains_open(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<xbrl />", headers={"content-type": "text/xml"})

    identity = FilingIdentity(stock_code="2330", year=2025, quarter="Q1")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await XBRLClient().download_xbrl_async(identity, tmp_path, client=client)
        assert result is not None
        assert result.read_bytes() == b"<xbrl />"
        assert not client.is_closed


@pytest.mark.asyncio
async def test_pdf_external_client_remains_open(tmp_path) -> None:
    filename = "202501_2330_AI1.pdf"

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, text=f'<a href="/pdf/{filename}">report</a>')
        return httpx.Response(200, content=b"%PDF-test")

    identity = FilingIdentity(stock_code="2330", year=2025, quarter="Q1")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await MOPSPDFClient().download_async(identity, tmp_path, client=client)
        assert result.read_bytes() == b"%PDF-test"
        assert not client.is_closed


@pytest.mark.asyncio
async def test_finmind_base_exception_result_is_provider_failure(monkeypatch) -> None:
    async def cancelled(*args, **kwargs):
        raise asyncio.CancelledError

    finmind = FinMindClient()
    monkeypatch.setattr(finmind, "_fetch_dataset", cancelled)
    identity = FilingIdentity(stock_code="2330", year=2025, quarter="Q1")

    async with httpx.AsyncClient() as client:
        assert await finmind.fetch_facts_async(identity, client=client) == []
        assert not client.is_closed


def test_pdf_url_parser_rejects_non_string_href() -> None:
    html = '<a href="one.pdf" class="report">ok</a><meta http-equiv="refresh">'
    assert MOPSPDFClient._parse_pdf_url(html, "one.pdf") == ("https://doc.twse.com.tw/one.pdf")


class TestFinMindUnitConversion:
    """FinMind reports full TWD; the canonical unit is thousands.

    The conversion used to be guarded by `abs(value) >= 1000`, which left any
    amount under NT$1,000 undivided and then labelled it thousands -- a silent
    1000x on the smallest values only. The convention is uniform, so the guard
    protected nothing.
    """

    @staticmethod
    def _facts(value, fm_type="Revenue"):
        from src.sources.finmind_client import FinMindClient

        return FinMindClient()._records_to_facts(
            [{"date": "2025-03-31", "type": fm_type, "value": value}], "2025-03-31"
        )

    def test_a_large_amount_converts_to_thousands(self):
        # TSMC 2024Q1 revenue arrives as full TWD and is NT$592.64bn.
        assert self._facts(592_644_201_000)[0]["value"] == 592_644_201

    def test_an_amount_below_one_thousand_is_still_converted(self):
        """The case the old guard mis-scaled by 1000x."""
        assert self._facts(500)[0]["value"] == 0.5

    def test_eps_is_excluded_by_unit_not_by_magnitude(self):
        fact = self._facts(7.82, fm_type="EPS")[0]
        assert fact["unit"] == "TWD_per_share"
        assert fact["value"] == 7.82

    def test_the_short_equity_spelling_is_not_an_income_field(self):
        """It used to map to net_income_attributable_to_parent."""
        fact = self._facts(41_588_114_000, fm_type="EquityAttributableToOwnersOfParent")[0]
        assert fact["field"] == "equity_attributable_to_parent"
        assert fact["period_type"] == "instant"

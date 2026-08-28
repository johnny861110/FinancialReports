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

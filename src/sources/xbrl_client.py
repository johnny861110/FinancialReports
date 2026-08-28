"""
XBRL and iXBRL document downloader — async-first.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

from src.domain.identity import FilingIdentity

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/html,*/*",
    "Referer": "https://mops.twse.com.tw/",
}


class XBRLClient:
    """Download XBRL and iXBRL instance documents from MOPS."""

    MOPS_URL = "https://mops.twse.com.tw"

    def __init__(self, timeout: int = 30, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries

    # ── async API ──────────────────────────────────────────────────────────────

    async def download_xbrl_async(
        self,
        identity: FilingIdentity,
        output_dir: Path,
        client: httpx.AsyncClient | None = None,
    ) -> Path | None:
        filename = f"{identity.period_code}_{identity.stock_code}_AI1.xml"
        return await self._fetch_first_async(
            identity,
            output_dir,
            filename,
            self._xbrl_urls(identity),
            ".xml",
            client,
        )

    async def download_ixbrl_async(
        self,
        identity: FilingIdentity,
        output_dir: Path,
        client: httpx.AsyncClient | None = None,
    ) -> Path | None:
        filename = f"{identity.period_code}_{identity.stock_code}_AI1.htm"
        return await self._fetch_first_async(
            identity,
            output_dir,
            filename,
            self._ixbrl_urls(identity),
            ".htm",
            client,
        )

    async def _fetch_first_async(
        self,
        identity: FilingIdentity,
        output_dir: Path,
        filename: str,
        urls: list[str],
        expected_suffix: str,
        client: httpx.AsyncClient | None,
    ) -> Path | None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / filename
        if dest.exists() and dest.stat().st_size > 512:
            return dest

        active_client = client
        own_client = active_client is None
        if active_client is None:
            active_client = httpx.AsyncClient(
                headers=_HEADERS, timeout=self.timeout, follow_redirects=True
            )
        try:
            for url in urls:
                result = await self._try_url_async(url, dest, expected_suffix, active_client)
                if result:
                    return result
        finally:
            if own_client:
                await active_client.aclose()

        logger.debug("%s not available for %s", expected_suffix, identity.filing_key)
        return None

    async def _try_url_async(
        self,
        url: str,
        dest: Path,
        expected_suffix: str,
        client: httpx.AsyncClient,
    ) -> Path | None:
        for attempt in range(1, self.max_retries + 1):
            try:
                async with client.stream("GET", url) as resp:
                    if resp.status_code == 404:
                        return None
                    resp.raise_for_status()
                    ct = resp.headers.get("content-type", "")
                    if "text/html" in ct and expected_suffix == ".xml":
                        return None
                    with open(dest, "wb") as f:
                        async for chunk in resp.aiter_bytes(65536):
                            f.write(chunk)
                logger.info("Downloaded %s -> %s", url, dest)
                return dest
            except httpx.HTTPStatusError:
                return None
            except httpx.HTTPError as exc:
                if attempt == self.max_retries:
                    logger.debug("Failed %s: %s", url, exc)
                    return None
                await asyncio.sleep(2**attempt)
        return None

    # ── sync fallbacks ─────────────────────────────────────────────────────────

    def download_xbrl(self, identity: FilingIdentity, output_dir: Path) -> Path | None:
        return asyncio.run(self.download_xbrl_async(identity, output_dir))

    def download_ixbrl(self, identity: FilingIdentity, output_dir: Path) -> Path | None:
        return asyncio.run(self.download_ixbrl_async(identity, output_dir))

    # ── URL builders ───────────────────────────────────────────────────────────

    def _xbrl_urls(self, identity: FilingIdentity) -> list[str]:
        b, sc, yr, pc = self.MOPS_URL, identity.stock_code, identity.year, identity.period_code
        return [
            f"{b}/xbrl/data/{yr}/{sc}/{pc}_{sc}_AI1.xml",
            f"{b}/xbrl/data/{yr}/{sc}/{pc}_{sc}.xml",
            f"{b}/openmkt/data/xbrl/{sc}/{yr}/{pc}_{sc}_AI1.xml",
        ]

    def _ixbrl_urls(self, identity: FilingIdentity) -> list[str]:
        b, sc, yr, pc = self.MOPS_URL, identity.stock_code, identity.year, identity.period_code
        return [
            f"{b}/xbrl/data/{yr}/{sc}/{pc}_{sc}_AI1.htm",
            f"{b}/xbrl/data/{yr}/{sc}/{pc}_{sc}.htm",
        ]

"""
TWSE/MOPS PDF downloader — async-first with sync fallback.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from src.domain.identity import FilingIdentity

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://doc.twse.com.tw/",
}


class MOPSPDFClient:
    """Download quarterly report PDFs from TWSE document server."""

    BASE_URL = "https://doc.twse.com.tw"
    QUERY_URL = f"{BASE_URL}/server-java/t57sb01"

    def __init__(self, timeout: int = 30, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries

    # ── async API ──────────────────────────────────────────────────────────────

    async def download_async(
        self,
        identity: FilingIdentity,
        output_dir: Path,
        client: httpx.AsyncClient | None = None,
    ) -> Path:
        """
        Async download. Reuse an existing AsyncClient if provided (recommended
        when downloading many files to share connection pool).
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        local_path = output_dir / identity.pdf_filename

        if local_path.exists() and local_path.stat().st_size > 1024:
            logger.info("PDF already exists: %s", local_path)
            return local_path

        own_client = client is None
        if own_client:
            client = httpx.AsyncClient(
                headers=_HEADERS, timeout=self.timeout, follow_redirects=True
            )

        try:
            pdf_url = await self._get_pdf_url_async(identity, client)
            await self._stream_download_async(pdf_url, local_path, client)
            return local_path
        finally:
            if own_client:
                await client.aclose()

    async def _get_pdf_url_async(self, identity: FilingIdentity, client: httpx.AsyncClient) -> str:
        payload = {
            "step": "9",
            "kind": "A",
            "co_id": identity.stock_code,
            "filename": identity.pdf_filename,
        }
        last_exc: Exception = FileNotFoundError("no attempts made")
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await client.post(self.QUERY_URL, data=payload)
                resp.raise_for_status()
                url = self._parse_pdf_url(resp.text, identity.pdf_filename)
                if url:
                    return url
                raise FileNotFoundError(f"No PDF link for {identity.filing_key}")
            except (httpx.HTTPError, FileNotFoundError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
        raise FileNotFoundError(f"Could not get PDF URL for {identity.filing_key}") from last_exc

    async def _stream_download_async(self, url: str, dest: Path, client: httpx.AsyncClient) -> None:
        for attempt in range(1, self.max_retries + 1):
            try:
                async with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    with open(dest, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                logger.info("Saved PDF: %s (%d bytes)", dest, dest.stat().st_size)
                return
            except httpx.HTTPError as exc:
                if attempt == self.max_retries:
                    raise
                logger.warning("Download attempt %d failed: %s", attempt, exc)
                await asyncio.sleep(2**attempt)

    # ── sync fallback ──────────────────────────────────────────────────────────

    def download(self, identity: FilingIdentity, output_dir: Path) -> Path:
        """Sync wrapper — calls the async implementation."""
        return asyncio.run(self.download_async(identity, output_dir))

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_pdf_url(html: str, filename: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        base = "https://doc.twse.com.tw"
        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            if filename in href or ".pdf" in href.lower():
                return href if href.startswith("http") else f"{base}/{href.lstrip('/')}"
        meta = soup.find("meta", attrs={"http-equiv": "refresh"})
        if meta and "content" in meta.attrs:
            content: str = meta["content"]
            if "url=" in content.lower():
                part = content.split("=", 1)[1].strip().strip("'\"")
                return part if part.startswith("http") else f"{base}/{part.lstrip('/')}"
        return None

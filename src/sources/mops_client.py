"""
MOPS (Market Observation Post System) auxiliary data client.
Provides company info and filing metadata lookups.
"""

from __future__ import annotations

import logging
from datetime import date

import requests
from bs4 import BeautifulSoup

from src.domain.identity import FilingIdentity

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://mops.twse.com.tw/",
}

# Known company names (fallback cache to reduce unnecessary requests)
_COMPANY_CACHE: dict[str, dict] = {}


class MOPSClient:
    """Fetch company metadata and filing info from MOPS."""

    MOPS_BASE = "https://mops.twse.com.tw"
    COMPANY_INFO_URL = f"{MOPS_BASE}/mops/web/ajax_t05st03"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)

    def get_company_info(self, stock_code: str) -> dict:
        """
        Return company metadata dict: {name_zh, industry, market}.
        Falls back to a placeholder if MOPS is unreachable.
        """
        if stock_code in _COMPANY_CACHE:
            return _COMPANY_CACHE[stock_code]

        info = self._fetch_company_info(stock_code)
        if info:
            _COMPANY_CACHE[stock_code] = info
        else:
            info = {"name_zh": stock_code, "industry": None, "market": None}
        return info

    def _fetch_company_info(self, stock_code: str) -> dict | None:
        """Try to fetch real company info from MOPS."""
        try:
            resp = self._session.post(
                self.COMPANY_INFO_URL,
                data={
                    "encodeURIComponent": "1",
                    "step": "1",
                    "firstin": "1",
                    "off": "1",
                    "co_id": stock_code,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return self._parse_company_info(resp.text)
        except Exception as exc:
            logger.debug("MOPS company info lookup failed for %s: %s", stock_code, exc)
            return None

    def _parse_company_info(self, html: str) -> dict | None:
        """Parse MOPS company info page."""
        try:
            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table")
            info: dict = {}
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cells) >= 2:
                        key, val = cells[0], cells[1]
                        if "公司名稱" in key or "名稱" in key:
                            info["name_zh"] = val
                        elif "產業類別" in key or "產業" in key:
                            info["industry"] = val
                        elif "上市" in key or "市場" in key:
                            info["market"] = val
            return info if info else None
        except Exception:
            return None

    def get_filing_date(self, identity: FilingIdentity) -> date | None:
        """
        Try to find the actual filing date for a quarterly report.
        Returns None if unavailable.
        """
        try:
            resp = self._session.post(
                f"{self.MOPS_BASE}/mops/web/ajax_t164sb03",
                data={
                    "encodeURIComponent": "1",
                    "step": "1",
                    "firstin": "1",
                    "co_id": identity.stock_code,
                    "year": str(identity.year - 1911),  # ROC year
                    "season": identity.QUARTER_MAP[identity.quarter],
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return self._parse_filing_date(resp.text)
        except Exception as exc:
            logger.debug("Filing date lookup failed for %s: %s", identity.filing_key, exc)
            return None

    def _parse_filing_date(self, html: str) -> date | None:
        """Extract filing date from MOPS response HTML."""
        try:
            soup = BeautifulSoup(html, "lxml")
            for td in soup.find_all("td"):
                text = td.get_text(strip=True)
                # MOPS dates in ROC format: YYY/MM/DD
                import re

                m = re.search(r"(\d{3})/(\d{2})/(\d{2})", text)
                if m:
                    roc_year = int(m.group(1))
                    month = int(m.group(2))
                    day = int(m.group(3))
                    return date(roc_year + 1911, month, day)
        except Exception:
            pass
        return None

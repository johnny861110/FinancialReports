"""
MOPS (Market Observation Post System) auxiliary data client.
Provides company info and filing metadata lookups.
"""

from __future__ import annotations

import logging
from datetime import date

import requests  # type: ignore[import-untyped]
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

# Open-data company directories published by the exchanges. MOPS's own
# company-info page (ajax_t05st03) now refuses scripted access, so the
# listing-wide OpenAPI datasets are the source. Each is one full list.
_DIRECTORIES = (
    # (url, market, code field, name field, industry field)
    (
        "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
        "上市",
        "公司代號",
        "公司簡稱",
        "產業別",
    ),
    (
        "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
        "上櫃",
        "SecuritiesCompanyCode",
        "CompanyAbbreviation",
        "SecuritiesIndustryCode",
    ),
    (
        "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R",
        "興櫃",
        "SecuritiesCompanyCode",
        "CompanyAbbreviation",
        "SecuritiesIndustryCode",
    ),
)

# Industry codes shared by both exchanges. A code missing here is kept as-is.
INDUSTRY_NAMES = {
    "01": "水泥工業",
    "02": "食品工業",
    "03": "塑膠工業",
    "04": "紡織纖維",
    "05": "電機機械",
    "06": "電器電纜",
    "08": "玻璃陶瓷",
    "09": "造紙工業",
    "10": "鋼鐵工業",
    "11": "橡膠工業",
    "12": "汽車工業",
    "14": "建材營造業",
    "15": "航運業",
    "16": "觀光餐旅",
    "17": "金融保險業",
    "18": "貿易百貨業",
    "20": "其他",
    "21": "化學工業",
    "22": "生技醫療業",
    "23": "油電燃氣業",
    "24": "半導體業",
    "25": "電腦及週邊設備業",
    "26": "光電業",
    "27": "通信網路業",
    "28": "電子零組件業",
    "29": "電子通路業",
    "30": "資訊服務業",
    "31": "其他電子業",
    "32": "文化創意業",
    "33": "農業科技業",
    "34": "電子商務",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
    "91": "存託憑證",
}

# stock_code -> {name_zh, industry, market}. Only a complete download is kept,
# so a failed fetch is retried on the next lookup instead of being remembered.
_DIRECTORY_CACHE: dict[str, dict] | None = None


class MOPSClient:
    """Fetch company metadata and filing info from MOPS."""

    MOPS_BASE = "https://mops.twse.com.tw"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)

    def get_company_info(self, stock_code: str) -> dict:
        """
        Return company metadata dict: {name_zh, industry, market}.

        Every value is None when the company cannot be found or the directories
        are unreachable; callers must not substitute the stock code for a name.
        """
        directory = self._load_directory()
        return dict(
            directory.get(stock_code) or {"name_zh": None, "industry": None, "market": None}
        )

    def _load_directory(self) -> dict[str, dict]:
        global _DIRECTORY_CACHE
        if _DIRECTORY_CACHE is not None:
            return _DIRECTORY_CACHE

        directory: dict[str, dict] = {}
        for url, market, code_key, name_key, industry_key in _DIRECTORIES:
            try:
                resp = self._session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                rows = resp.json()
            except Exception as exc:
                logger.warning("Company directory fetch failed (%s): %s", url, exc)
                return directory
            # Entries are ordered highest listing first; a company that appears in
            # more than one list (it moved up a board) keeps the earlier entry.
            for code, info in self._parse_directory(
                rows, market, code_key, name_key, industry_key
            ).items():
                directory.setdefault(code, info)

        _DIRECTORY_CACHE = directory
        return directory

    @staticmethod
    def _parse_directory(
        rows: object, market: str, code_key: str, name_key: str, industry_key: str
    ) -> dict[str, dict]:
        """Index one OpenAPI company list by stock code."""
        parsed: dict[str, dict] = {}
        if not isinstance(rows, list):
            return parsed
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get(code_key) or "").strip()
            name = str(row.get(name_key) or "").strip()
            if not code or not name:
                continue
            industry = str(row.get(industry_key) or "").strip() or None
            parsed[code] = {
                "name_zh": name,
                "industry": INDUSTRY_NAMES.get(industry, industry) if industry else None,
                "market": market,
            }
        return parsed

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

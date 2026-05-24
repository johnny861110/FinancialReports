"""
Company identity resolution: DB lookup, MOPS fallback, placeholder.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.sources.mops_client import MOPSClient
    from src.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


def resolve_company(
    stock_code: str,
    store: SQLiteStore,
    mops_client: MOPSClient | None = None,
) -> tuple[int, str]:
    """
    Resolve a company by stock code.

    Strategy:
    1. Check DB for existing company record
    2. If not found, try MOPS lookup (if mops_client provided)
    3. If not found, use stock_code as name placeholder

    Returns (company_id, company_name_zh).
    """
    # 1. Check DB
    with store.conn() as c:
        from sqlalchemy import text

        row = c.execute(
            text("SELECT id, name_zh FROM companies WHERE stock_code=:sc"),
            {"sc": stock_code},
        ).fetchone()
    if row:
        return row[0], row[1] or stock_code

    # 2. Try MOPS
    name_zh = stock_code
    industry = None
    market = None

    if mops_client is not None:
        try:
            info = mops_client.get_company_info(stock_code)
            name_zh = info.get("name_zh") or stock_code
            industry = info.get("industry")
            market = info.get("market")
            logger.info("Resolved company %s -> '%s' from MOPS", stock_code, name_zh)
        except Exception as exc:
            logger.warning("MOPS company lookup failed for %s: %s", stock_code, exc)

    # 3. Upsert (with or without MOPS data)
    company_id = store.upsert_company(
        stock_code=stock_code,
        name_zh=name_zh,
        industry=industry,
        market=market,
    )
    return company_id, name_zh

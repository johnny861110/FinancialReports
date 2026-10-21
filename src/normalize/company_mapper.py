"""
Company identity resolution: DB lookup, exchange directory, NULL when unknown.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.sources.mops_client import MOPSClient
    from src.storage.store import FilingStore

logger = logging.getLogger(__name__)


def resolve_company(
    stock_code: str,
    store: FilingStore,
    mops_client: MOPSClient | None = None,
) -> tuple[int, str]:
    """
    Resolve a company by stock code.

    Strategy:
    1. Check DB for existing company record; a real name ends the lookup
    2. Otherwise (no row, NULL name, or the stock code stored as a name) ask the
       company directory and write what it knows
    3. If the directory has nothing, store NULL -- never the stock code

    Returns (company_id, company_name_zh); the name falls back to the stock code
    for display only.
    """
    from sqlalchemy import text

    with store.conn() as c:
        row = c.execute(
            text("SELECT id, name_zh FROM companies WHERE stock_code=:sc"),
            {"sc": stock_code},
        ).fetchone()
    if row and row[1] and row[1] != stock_code:
        return row[0], row[1]

    name_zh: str | None = None
    industry = None
    market = None

    if mops_client is not None:
        try:
            info = mops_client.get_company_info(stock_code)
            name_zh = info.get("name_zh") or None
            industry = info.get("industry")
            market = info.get("market")
        except Exception as exc:
            logger.warning("Company lookup failed for %s: %s", stock_code, exc)
        if name_zh:
            logger.info("Resolved company %s -> '%s'", stock_code, name_zh)
        else:
            logger.warning("No company name found for %s", stock_code)

    if row and not name_zh:
        # Nothing new to write; leave the row alone.
        return row[0], stock_code

    company_id = store.upsert_company(
        stock_code=stock_code,
        name_zh=name_zh,
        industry=industry,
        market=market,
    )
    return company_id, name_zh or stock_code


def backfill_companies(
    store: FilingStore, mops_client: MOPSClient, *, dry_run: bool = False
) -> list[tuple[str, tuple, tuple]]:
    """
    Repair stored company rows from the exchange directory. Safe to re-run.

    A row found in the directory takes the directory's name, industry and market.
    A row not found keeps real data it already has, but a stock code stored as
    its own name is cleared to NULL. Returns (stock_code, before, after) for each
    row that changed, where each tuple is (name_zh, industry, market).
    """
    from sqlalchemy import text

    with store.conn() as c:
        rows = c.execute(
            text("SELECT stock_code, name_zh, industry, market FROM companies ORDER BY stock_code")
        ).fetchall()

    changes: list[tuple[str, tuple, tuple]] = []
    for stock_code, name_zh, industry, market in rows:
        before = (name_zh, industry, market)
        info = mops_client.get_company_info(stock_code)
        if info.get("name_zh"):
            after = (info["name_zh"], info.get("industry"), info.get("market"))
        elif name_zh == stock_code:
            after = (None, industry, market)
        else:
            after = before
        if after == before:
            continue
        changes.append((stock_code, before, after))
        if not dry_run:
            with store.conn() as c:
                c.execute(
                    text(
                        "UPDATE companies SET name_zh=:nz, industry=:ind, market=:mkt"
                        " WHERE stock_code=:sc"
                    ),
                    {"nz": after[0], "ind": after[1], "mkt": after[2], "sc": stock_code},
                )
    return changes

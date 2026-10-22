"""
Rewrite period_start on FinMind duration facts stored under the old labelling.

Every duration used to start on Jan 1, which is right for Q1, for cash flow
(year-to-date) and for a semiannual filer's Q2, and wrong for the income
statement of Q2-Q4 (single-quarter). Only period_start changes, and a row that
already holds the right value is left alone, so a second run does nothing.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import text

from src.domain.identity import FilingIdentity
from src.domain.taxonomy import CANONICAL_CASHFLOW
from src.normalize.period_normalizer import SEMIANNUAL_MARKETS, finmind_period_start
from src.storage.store import FilingStore

logger = logging.getLogger(__name__)


@dataclass
class RelabelSummary:
    examined: int = 0
    # (quarter, dataset) -> rows whose period_start is (or would be) rewritten
    changed: Counter = field(default_factory=Counter)

    @property
    def total_changed(self) -> int:
        return sum(self.changed.values())


def relabel_periods(
    store: FilingStore, *, stock: str | None = None, dry_run: bool = False
) -> RelabelSummary:
    """Correct period_start on finmind duration facts. Safe to re-run."""
    query = (
        "SELECT ff.id, f.filing_key, ff.field, ff.period_start, c.market"
        " FROM financial_facts ff"
        " JOIN filings f ON f.id = ff.filing_id"
        " JOIN companies c ON c.id = f.company_id"
        " WHERE ff.source_type = 'finmind' AND ff.period_type = 'duration'"
    )
    params: dict = {}
    if stock:
        query += " AND c.stock_code = :stock"
        params["stock"] = stock
    query += " ORDER BY ff.id"

    with store.conn() as conn:
        rows = conn.execute(text(query), params).fetchall()

    summary = RelabelSummary(examined=len(rows))
    updates: list[dict] = []
    for fact_id, filing_key, fact_field, current, market in rows:
        identity = FilingIdentity.from_filing_key(filing_key)
        target = finmind_period_start(
            identity, fact_field, semiannual=market in SEMIANNUAL_MARKETS
        ).isoformat()
        if current == target:
            continue
        dataset = "cash_flow" if fact_field in CANONICAL_CASHFLOW else "income"
        summary.changed[(identity.quarter, dataset)] += 1
        updates.append({"id": fact_id, "ps": target})

    if updates and not dry_run:
        with store.conn() as conn:
            conn.execute(text("UPDATE financial_facts SET period_start=:ps WHERE id=:id"), updates)
    return summary

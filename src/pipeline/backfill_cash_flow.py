"""
Add operating_cash_flow_quarter to filings stored before the fact existed, and
rebuild the analytics that read it (cf_quality, QoQ, the cash-flow card).

One read-only FinMind request per filing, sequential with a pause. Only facts and
analytics rows change: document text, chunks and embeddings are never touched,
so unlike a re-extract this is safe on a filing that already has them. Safe to
re-run; a filing whose previous quarter FinMind does not return gets no fact and
keeps the analytics it had, minus a cf_quality that cannot be computed.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass, field

import httpx
from sqlalchemy import text

from src.domain.identity import FilingIdentity
from src.domain.models import Fact
from src.normalize.period_normalizer import (
    SEMIANNUAL_MARKETS,
    finmind_period_start,
    quarter_to_dates,
)
from src.pipeline.build_insights import rebuild_analytics
from src.sources.finmind_client import (
    FinMindClient,
    _period_end_date,
    operating_cash_flow_quarter,
    ytd_operating_cash_flow,
)
from src.storage.store import FilingStore

logger = logging.getLogger(__name__)

FIELD = "operating_cash_flow_quarter"
# FinMind's free tier is rate limited; one request per filing, this long apart.
REQUEST_DELAY_SECONDS = 1.0


@dataclass
class Outcome:
    filing_key: str
    quarter: str
    # added | unchanged | no_current_row | no_previous_row | failed
    status: str
    value: float | None = None
    cf_quality_before: float | None = None
    cf_quality_after: float | None = None


@dataclass
class BackfillSummary:
    outcomes: list[Outcome] = field(default_factory=list)

    def by_quarter(self) -> dict[str, Counter]:
        table: dict[str, Counter] = {}
        for o in self.outcomes:
            table.setdefault(o.quarter, Counter())[o.status] += 1
        return table


def _cf_quality(store: FilingStore, filing_id: int) -> float | None:
    with store.conn() as c:
        return c.execute(
            text(
                "SELECT value FROM financial_metrics WHERE filing_id=:f AND metric_name='cf_quality'"
            ),
            {"f": filing_id},
        ).scalar_one_or_none()


def _filings(store: FilingStore, stock: str | None) -> list:
    query = (
        "SELECT f.id, f.filing_key, f.status, c.market FROM filings f"
        " JOIN companies c ON c.id = f.company_id"
        " WHERE EXISTS (SELECT 1 FROM financial_facts ff WHERE ff.filing_id = f.id"
        " AND ff.source_type = 'finmind')"
    )
    params: dict = {}
    if stock:
        query += " AND c.stock_code = :stock"
        params["stock"] = stock
    with store.conn() as c:
        return [tuple(r) for r in c.execute(text(query + " ORDER BY f.filing_key"), params)]


async def backfill_cash_flow_quarter(
    store: FilingStore,
    *,
    stock: str | None = None,
    dry_run: bool = False,
    delay: float = REQUEST_DELAY_SECONDS,
    client: httpx.AsyncClient | None = None,
) -> BackfillSummary:
    """Fetch, store and recompute per filing. With dry_run nothing is written."""
    summary = BackfillSummary()
    finmind = FinMindClient()
    own_client = client is None
    http = client or httpx.AsyncClient(
        timeout=finmind.timeout,
        follow_redirects=True,
        verify=False,  # WSL SSL chain issue, as in FinMindClient
        headers={"User-Agent": "Mozilla/5.0 Chrome/120"},
    )
    try:
        for index, (filing_id, filing_key, status, market) in enumerate(_filings(store, stock)):
            identity = FilingIdentity.from_filing_key(filing_key)
            outcome = Outcome(filing_key, identity.quarter, "failed")
            outcome.cf_quality_before = _cf_quality(store, filing_id)
            summary.outcomes.append(outcome)
            if index and delay:
                await asyncio.sleep(delay)
            semiannual = market in SEMIANNUAL_MARKETS
            try:
                records = await finmind.fetch_cash_flow_records_async(identity, http)
            except Exception as exc:
                logger.warning("FinMind cash flow failed for %s: %s", filing_key, exc)
                continue

            value = operating_cash_flow_quarter(records, identity, semiannual=semiannual)
            existing = next((f["value"] for f in store.get_facts(filing_key, [FIELD])), None)
            outcome.value = value
            if value is not None:
                outcome.status = "unchanged" if existing == value else "added"
            elif ytd_operating_cash_flow(records, _period_end_date(identity)) is None:
                outcome.status = "no_current_row"
            else:
                outcome.status = "no_previous_row"
            net_income = next(
                (f["value"] for f in store.get_facts(filing_key, ["net_income"])), None
            )
            outcome.cf_quality_after = (
                round(value / net_income, 4) if value is not None and net_income else None
            )
            if dry_run:
                continue
            if value is not None:
                _, period_end = quarter_to_dates(identity)
                store.save_fact(
                    filing_id,
                    Fact(
                        filing_key=filing_key,
                        field=FIELD,
                        value=value,
                        unit="TWD_thousands",
                        period_start=finmind_period_start(identity, FIELD, semiannual=semiannual),
                        period_end=period_end,
                        period_type="duration",
                        source_type="finmind",
                        confidence=0.9,
                    ),
                )
            # Rebuilt even without a fact: the old cf_quality was YTD over a quarter
            # and must go rather than linger beside a filing that cannot recompute it.
            if status == "insight_ready":
                rebuild_analytics(identity, store, filing_id)
    finally:
        if own_client:
            await http.aclose()
    return summary

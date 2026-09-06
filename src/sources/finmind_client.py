"""
FinMind API client — the structured financial data source for this project.

FinMind is the *primary* source of canonical facts, by deliberate choice, not a
fallback for XBRL. Every fact in the corpus carries source_type "finmind" and no
filing holds an XBRL or iXBRL source document; that is the expected shape of
this system. Code elsewhere still speaks of an "XBRL fallback" for historical
reasons and the XBRL parsers still exist, but nothing feeds them today.

This matters because the absence looks exactly like a bug from the inside: the
schema has xbrl_tag columns, the taxonomy lists XBRL tags per field, the
pipeline has an XBRL branch that never fires, and the quality score docks marks
for source coverage FinMind cannot supply. Before "fixing" any of that, note
that the source decision is settled -- see docs/CHANGE-RECORD-2026-09-06.md.

Free tier: no auth required, rate-limited.
Datasets used:
  - TaiwanStockFinancialStatements  (income statement)
  - TaiwanStockBalanceSheet         (balance sheet)
  - TaiwanStockCashFlowsStatement   (cash flow)
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from src.domain.identity import FilingIdentity

logger = logging.getLogger(__name__)

_BASE = "https://api.finmindtrade.com/api/v4/data"

# FinMind type → canonical field name
_FINMIND_TO_CANONICAL: dict[str, str] = {
    # Income statement
    "Revenue": "net_revenue",
    "GrossProfit": "gross_profit",
    "OperatingIncome": "operating_income",
    "IncomeBeforeTax": "profit_before_tax",
    "PreTaxIncome": "profit_before_tax",
    "IncomeAfterTaxes": "net_income",
    "IncomeAfterTax": "net_income",  # bank variant
    "IncomeFromContinuingOperations": "net_income",  # bank variant
    "EPS": "eps_basic",
    "BasicEPS": "eps_basic",
    "DilutedEPS": "eps_diluted",
    "OperatingExpenses": "operating_expenses",
    "ResearchAndDevelopmentExpenses": "rd_expenses",
    "TAX": "tax_expense",
    "TotalConsolidatedProfitForThePeriod": "comprehensive_income",
    # Bank-specific income fields
    "NetInterestIncome": "net_interest_income",
    "NetNonInterestIncome": "net_non_interest_income",
    "BadDebts": "loan_loss_provisions",
    # Balance sheet
    "CashAndCashEquivalents": "cash_and_equivalents",
    "AccountsReceivableNet": "accounts_receivable",  # FinMind actual key
    "AccountsReceivable": "accounts_receivable",  # fallback
    "Inventories": "inventory",
    "CurrentAssets": "current_assets",
    "TotalAssets": "total_assets",  # FinMind actual key
    "Assets": "total_assets",  # fallback
    "AccountsPayable": "accounts_payable",
    "CurrentLiabilities": "current_liabilities",
    "Liabilities": "total_liabilities",
    "Equity": "equity",
    # FinMind emits two spellings for the same balance-sheet concept. The short
    # one used to be mapped to net_income_attributable_to_parent, which put an
    # equity figure into an income-statement field: 3661_2025Q1 reported
    # 41,588,114 against a net_income of 1,461,343 -- 28x the total, and equal
    # to `equity` 41,607,063 less non-controlling interests. taxonomy.py is the
    # authority and assigns this tag to equity_attributable_to_parent; the
    # income field's tag is ProfitLossAttributableToOwnersOfParent, which
    # FinMind does not supply. So net_income_attributable_to_parent is now
    # simply unpopulated from FinMind, which is correct -- absent beats wrong.
    "EquityAttributableToOwnersOfParent": "equity_attributable_to_parent",
    "EquityAttributableToOwnersOfParentCompany": "equity_attributable_to_parent",
    "RetainedEarnings": "retained_earnings",
    "CapitalStock": "share_capital",  # FinMind actual key
    "OrdinaryShare": "share_capital",  # FinMind alternate key
    "CommonStocks": "share_capital",  # fallback
    # Cash flow
    "CashFlowsFromOperatingActivities": "operating_cash_flow",  # FinMind actual key
    "NetCashInflowFromOperatingActivities": "operating_cash_flow",  # alias
    "CashProvidedByInvestingActivities": "investing_cash_flow",
    "CashFlowsProvidedFromFinancingActivities": "financing_cash_flow",  # FinMind actual key
    "CashProvidedByFinancingActivities": "financing_cash_flow",  # fallback
    "PropertyAndPlantAndEquipment": "capex",
    "CashBalancesBeginningOfPeriod": "cash_beginning",
    "CashBalancesEndOfPeriod": "cash_ending",
}

# Fields that are point-in-time (balance sheet) rather than period
_INSTANT_FIELDS = {
    "cash_and_equivalents",
    "accounts_receivable",
    "inventory",
    "current_assets",
    "total_assets",
    "accounts_payable",
    "current_liabilities",
    "total_liabilities",
    "equity",
    "equity_attributable_to_parent",
    "retained_earnings",
    "share_capital",
    "cash_ending",
}


def _period_end_date(identity: FilingIdentity) -> str:
    """Return the last day of the quarter as YYYY-MM-DD."""
    quarter_end = {
        1: "03-31",
        2: "06-30",
        3: "09-30",
        4: "12-31",
        "Q1": "03-31",
        "Q2": "06-30",
        "Q3": "09-30",
        "Q4": "12-31",
        "1": "03-31",
        "2": "06-30",
        "3": "09-30",
        "4": "12-31",
    }
    return f"{identity.year}-{quarter_end[identity.quarter]}"


class FinMindClient:
    """Fetch structured financial data from FinMind free API."""

    _DATASETS = [
        "TaiwanStockFinancialStatements",
        "TaiwanStockBalanceSheet",
        "TaiwanStockCashFlowsStatement",
    ]

    def __init__(self, token: str | None = None, timeout: int = 30) -> None:
        self.token = token  # optional paid-tier token
        self.timeout = timeout

    async def fetch_facts_async(
        self,
        identity: FilingIdentity,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict]:
        """
        Fetch all three statements for a filing and return canonical fact dicts.
        Each dict has: field, value, unit, period_type
        """
        period_end = _period_end_date(identity)
        # Start of year for the annual range query
        start_date = f"{identity.year}-01-01"

        active_client = client
        own_client = active_client is None
        if active_client is None:
            active_client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False,  # WSL SSL chain issue
                headers={"User-Agent": "Mozilla/5.0 Chrome/120"},
            )
        try:
            tasks = [
                self._fetch_dataset(ds, identity.stock_code, start_date, period_end, active_client)
                for ds in self._DATASETS
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            if own_client:
                await active_client.aclose()

        facts: list[dict] = []
        for ds, result in zip(self._DATASETS, results):
            if isinstance(result, BaseException):
                logger.warning("FinMind %s failed for %s: %s", ds, identity.filing_key, result)
                continue
            facts.extend(self._records_to_facts(result, period_end))

        logger.info("FinMind fetched %d facts for %s", len(facts), identity.filing_key)
        return facts

    async def _fetch_dataset(
        self,
        dataset: str,
        stock_id: str,
        start_date: str,
        end_date: str,
        client: httpx.AsyncClient,
    ) -> list[dict]:
        params: dict = {
            "dataset": dataset,
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        if self.token:
            params["token"] = self.token

        for attempt in range(1, 4):
            try:
                resp = await client.get(_BASE, params=params)
                resp.raise_for_status()
                body = resp.json()
                if body.get("status") != 200:
                    raise ValueError(f"FinMind API error: {body.get('msg')}")
                return body.get("data", [])
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(2**attempt)
        return []

    def _records_to_facts(self, records: list[dict], period_end: str) -> list[dict]:
        """Convert raw FinMind records to canonical fact dicts."""
        facts: list[dict] = []
        # Keep only records matching the target quarter-end date
        for rec in records:
            if rec.get("date") != period_end:
                continue
            fm_type = rec.get("type", "")
            # Skip percentage columns (type ends with _per)
            if fm_type.endswith("_per"):
                continue
            canonical = _FINMIND_TO_CANONICAL.get(fm_type)
            if not canonical:
                continue
            value = rec.get("value")
            if value is None:
                continue
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            period_type = "instant" if canonical in _INSTANT_FIELDS else "duration"
            unit = "TWD_per_share" if canonical.startswith("eps") else "TWD_thousands"
            # FinMind reports full TWD, so this converts to the canonical
            # thousands. It used to be guarded by `abs(value) >= 1000`, which
            # created a silent 1000x cliff: an amount under NT$1,000 was left
            # undivided and then labelled thousands. The convention is uniform
            # -- 2330_2024Q1 net_revenue arrives as 592,644,201,000 and
            # 592,644,201 thousands is TSMC's published figure -- so there is
            # nothing for the guard to protect and it only mis-scales the
            # smallest values. EPS is excluded by unit, not by magnitude.
            if unit == "TWD_thousands":
                value = value / 1000.0

            facts.append(
                {
                    "field": canonical,
                    "value": value,
                    "unit": unit,
                    "period_type": period_type,
                    "confidence": 0.95,
                    "xbrl_tag": fm_type,
                }
            )
        return facts

    def fetch_facts(self, identity: FilingIdentity) -> list[dict]:
        """Sync wrapper."""
        return asyncio.run(self.fetch_facts_async(identity))

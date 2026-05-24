"""
Financial metrics computation.
Pure functions over dict[str, float] — no database access.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """Safe division returning None on zero denominator or None inputs."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def compute_margins(facts: dict[str, float]) -> dict[str, float | None]:
    """
    Compute income statement margin ratios.

    Returns:
      gross_margin    = gross_profit / net_revenue
      operating_margin = operating_income / net_revenue
      net_margin      = net_income / net_revenue
    """
    rev = facts.get("net_revenue")
    return {
        "gross_margin": _safe_div(facts.get("gross_profit"), rev),
        "operating_margin": _safe_div(facts.get("operating_income"), rev),
        "net_margin": _safe_div(facts.get("net_income"), rev),
    }


def compute_ratios(facts: dict[str, float]) -> dict[str, float | None]:
    """
    Compute balance sheet and profitability ratios.

    Returns:
      current_ratio       = current_assets / current_liabilities
      debt_to_equity      = total_liabilities / equity
      roe                 = net_income / equity
      roa                 = net_income / total_assets
      book_value_per_share (proxy: equity / share_capital * 10 assuming 10 NT$ par)
    """
    equity = facts.get("equity")
    total_assets = facts.get("total_assets")
    net_income = facts.get("net_income")
    share_capital = facts.get("share_capital")

    bvps = None
    if equity is not None and share_capital and share_capital > 0:
        # shares outstanding ≈ share_capital / 10 (NT$10 par value)
        shares = share_capital / 10
        bvps = equity / shares

    return {
        "current_ratio": _safe_div(facts.get("current_assets"), facts.get("current_liabilities")),
        "debt_to_equity": _safe_div(facts.get("total_liabilities"), equity),
        "roe": _safe_div(net_income, equity),
        "roa": _safe_div(net_income, total_assets),
        "book_value_per_share": bvps,
    }


def compute_fcf(facts: dict[str, float]) -> dict[str, float | None]:
    """
    Compute free cash flow.

    free_cash_flow = operating_cash_flow - |capex|
    capex is typically reported as negative in cash flow statements.
    """
    ocf = facts.get("operating_cash_flow")
    capex = facts.get("capex")
    if ocf is None:
        return {"free_cash_flow": None}
    if capex is None:
        return {"free_cash_flow": ocf}
    # capex may be negative (outflow) or positive depending on source
    fcf = ocf - abs(capex)
    return {"free_cash_flow": fcf}


def compute_all_metrics(facts: dict[str, float]) -> dict[str, float]:
    """
    Run all metric computations.
    Skip silently if required facts are missing.
    Returns a flat dict of {metric_name: value} with only non-None values.
    """
    result: dict[str, float] = {}

    for name, value in compute_margins(facts).items():
        if value is not None:
            result[name] = round(value, 6)

    for name, value in compute_ratios(facts).items():
        if value is not None:
            result[name] = round(value, 6)

    for name, value in compute_fcf(facts).items():
        if value is not None:
            result[name] = value

    # Supplementary: R&D intensity
    rev = facts.get("net_revenue")
    rd = facts.get("rd_expenses")
    if rev and rd and rev > 0:
        result["rd_intensity"] = round(rd / rev, 6)

    # Cash flow quality: OCF / net_income
    ocf = facts.get("operating_cash_flow")
    ni = facts.get("net_income")
    if ocf is not None and ni is not None and ni != 0:
        result["cf_quality"] = round(ocf / ni, 4)

    return result

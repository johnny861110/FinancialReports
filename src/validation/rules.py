"""
Financial data validation rules.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Metadata for a validation rule."""

    rule_id: str
    description: str
    severity: str  # "error" | "warning" | "info"


def check_balance_sheet_equation(facts: dict[str, float]) -> tuple[bool, str]:
    """
    Assets = Liabilities + Equity (within 1% tolerance).
    """
    assets = facts.get("total_assets")
    liabilities = facts.get("total_liabilities")
    equity = facts.get("equity")

    if assets is None or liabilities is None or equity is None:
        return True, "Insufficient data to check balance sheet equation"

    lhs = assets
    rhs = liabilities + equity
    if rhs == 0:
        return True, "Cannot check equation with zero liabilities+equity"

    discrepancy_pct = abs(lhs - rhs) / abs(rhs) * 100
    if discrepancy_pct <= 1.0:
        return True, f"Balance sheet equation holds (discrepancy {discrepancy_pct:.3f}%)"
    return (
        False,
        f"Balance sheet equation fails: assets={assets:,.0f} != liabilities+equity={rhs:,.0f}"
        f" (discrepancy {discrepancy_pct:.2f}%)",
    )


def check_gross_profit_lte_revenue(facts: dict[str, float]) -> tuple[bool, str]:
    """
    Gross profit <= Net revenue.
    """
    gp = facts.get("gross_profit")
    rev = facts.get("net_revenue")
    if gp is None or rev is None:
        return True, "Insufficient data to check gross profit vs revenue"
    if gp <= rev:
        return True, f"Gross profit ({gp:,.0f}) <= revenue ({rev:,.0f}) — OK"
    return (
        False,
        f"Gross profit ({gp:,.0f}) exceeds revenue ({rev:,.0f}) — data error",
    )


def check_income_consistency(facts: dict[str, float]) -> tuple[bool, str]:
    """
    Operating income <= Gross profit (gross profit ≥ operating income).
    """
    oi = facts.get("operating_income")
    gp = facts.get("gross_profit")
    if oi is None or gp is None:
        return True, "Insufficient data to check income consistency"
    # Operating income can be negative (loss), but gross profit should be >= operating income
    if oi <= gp:
        return True, f"Operating income ({oi:,.0f}) <= gross profit ({gp:,.0f}) — OK"
    return (
        False,
        f"Operating income ({oi:,.0f}) exceeds gross profit ({gp:,.0f}) — possible data error",
    )


def check_eps_consistency(facts: dict[str, float]) -> tuple[bool, str]:
    """
    EPS sign should be consistent with net income sign.
    """
    ni = facts.get("net_income")
    eps = facts.get("eps_basic")
    if ni is None or eps is None:
        return True, "Insufficient data to check EPS consistency"
    ni_positive = ni >= 0
    eps_positive = eps >= 0
    if ni_positive == eps_positive:
        return True, f"EPS ({eps:.2f}) sign consistent with net income ({ni:,.0f})"
    return (
        False,
        f"EPS ({eps:.2f}) sign inconsistent with net income ({ni:,.0f})",
    )


def check_current_ratio_positive(facts: dict[str, float]) -> tuple[bool, str]:
    """
    Current assets and current liabilities should be positive.
    """
    ca = facts.get("current_assets")
    cl = facts.get("current_liabilities")
    if ca is None or cl is None:
        return True, "Insufficient data for current ratio check"
    if ca >= 0 and cl > 0:
        return True, "Current assets/liabilities are positive — OK"
    return False, f"Unexpected negative values: current_assets={ca}, current_liabilities={cl}"


# Liabilities the source should never report below zero. current_liabilities is
# already covered by check_current_ratio_positive; this catches the rest.
_NON_NEGATIVE_LIABILITIES = ("accounts_payable", "total_liabilities")


def check_liabilities_not_negative(facts: dict[str, float]) -> tuple[bool, str]:
    """
    A liability cannot be negative.

    FinMind returns AccountsPayable below zero for some companies and not
    others -- 22 of 62 rows across 8 companies in the present corpus -- and it
    is the only balance-sheet field that is ever negative. The sign convention
    is inconsistent at the source rather than uniformly flipped, so the value is
    left exactly as the provider gave it: normalising it here would write a
    guess into stored data and hide the disagreement. Flagging it instead lets a
    consumer see the figure is suspect and leaves the convention to a human.
    """
    offenders = [
        (field, facts[field])
        for field in _NON_NEGATIVE_LIABILITIES
        if facts.get(field) is not None and facts[field] < 0
    ]
    if not offenders:
        return True, "Liabilities are non-negative — OK"
    detail = ", ".join(f"{field}={value:,.0f}" for field, value in offenders)
    return False, f"Liability reported as negative, source sign convention suspect: {detail}"


def check_cash_flow_signs(facts: dict[str, float]) -> tuple[bool, str]:
    """
    Investing and financing cash flows are commonly negative; operating commonly positive for profitable companies.
    This is an informational check only.
    """
    ocf = facts.get("operating_cash_flow")
    if ocf is None:
        return True, "No operating cash flow data"
    if ocf < 0:
        return (
            True,  # Pass but note it
            f"WARNING: Negative operating cash flow ({ocf:,.0f}) may indicate cash burn",
        )
    return True, f"Operating cash flow positive ({ocf:,.0f}) — OK"


# Registry of all rules with metadata
RuleCheck = Callable[[dict[str, float]], tuple[bool, str]]

ALL_RULES: list[tuple[ValidationRule, RuleCheck]] = [
    (
        ValidationRule("balance_sheet_equation", "Assets = Liabilities + Equity", "error"),
        check_balance_sheet_equation,
    ),
    (
        ValidationRule("gross_profit_lte_revenue", "Gross profit ≤ Net revenue", "error"),
        check_gross_profit_lte_revenue,
    ),
    (
        ValidationRule("income_consistency", "Operating income ≤ Gross profit", "warning"),
        check_income_consistency,
    ),
    (
        ValidationRule("eps_consistency", "EPS sign matches net income sign", "warning"),
        check_eps_consistency,
    ),
    (
        ValidationRule(
            "current_ratio_positive", "Current assets/liabilities are positive", "error"
        ),
        check_current_ratio_positive,
    ),
    (
        ValidationRule(
            "liabilities_not_negative", "Liabilities are not reported negative", "error"
        ),
        check_liabilities_not_negative,
    ),
    (
        ValidationRule("cash_flow_signs", "Operating cash flow sign check", "info"),
        check_cash_flow_signs,
    ),
]


def run_all_rules(facts: dict[str, float]) -> list[dict]:
    """
    Run all validation rules against a facts dict.
    Returns list of {rule_id, passed, severity, message}.
    """
    results: list[dict] = []
    for rule, check_fn in ALL_RULES:
        try:
            passed, message = check_fn(facts)
            results.append(
                {
                    "rule_id": rule.rule_id,
                    "passed": passed,
                    "severity": rule.severity,
                    "message": message,
                }
            )
        except Exception as exc:
            logger.warning("Rule %s raised exception: %s", rule.rule_id, exc)
            results.append(
                {
                    "rule_id": rule.rule_id,
                    "passed": False,
                    "severity": rule.severity,
                    "message": f"Rule check error: {exc}",
                }
            )
    return results

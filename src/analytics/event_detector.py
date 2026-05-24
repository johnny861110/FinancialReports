"""
Rule-based financial event detection.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EventRule:
    """Definition of a detectable financial event."""

    event_type: str
    severity: str  # "error" | "warning" | "info"
    title: str
    description_template: str  # supports {value:.1f} style formatting
    check: Callable[[dict, dict, list, list], bool]


def _get_yoy_change_pct(yoy_changes: list[dict], field: str) -> float | None:
    """Get YoY change % for a specific field."""
    for c in yoy_changes:
        if c["field"] == field:
            return c.get("change_pct")
    return None


def _get_qoq_change_pct(qoq_changes: list[dict], field: str) -> float | None:
    """Get QoQ change % for a specific field."""
    for c in qoq_changes:
        if c["field"] == field:
            return c.get("change_pct")
    return None


EVENT_RULES: list[EventRule] = [
    EventRule(
        event_type="revenue_growth_acceleration",
        severity="info",
        title="Revenue Growth Acceleration",
        description_template="Revenue grew {change_pct:.1f}% YoY, exceeding 30% threshold.",
        check=lambda facts, metrics, yoy, qoq: (lambda pct: pct is not None and pct > 30)(
            _get_yoy_change_pct(yoy, "net_revenue")
        ),
    ),
    EventRule(
        event_type="revenue_decline",
        severity="warning",
        title="Revenue Decline",
        description_template="Revenue declined {change_pct:.1f}% YoY.",
        check=lambda facts, metrics, yoy, qoq: (lambda pct: pct is not None and pct < -10)(
            _get_yoy_change_pct(yoy, "net_revenue")
        ),
    ),
    EventRule(
        event_type="gross_margin_compression",
        severity="warning",
        title="Gross Margin Compression",
        description_template="Gross margin compressed by more than 3 percentage points YoY.",
        check=lambda facts, metrics, yoy, qoq: (lambda pct: pct is not None and pct < -3)(
            _get_yoy_change_pct(yoy, "gross_profit")
        ),
    ),
    EventRule(
        event_type="fcf_negative",
        severity="warning",
        title="Negative Free Cash Flow",
        description_template="Free cash flow is negative: {value:.0f} TWD thousands.",
        check=lambda facts, metrics, yoy, qoq: (
            metrics.get("free_cash_flow") is not None and metrics["free_cash_flow"] < 0
        ),
    ),
    EventRule(
        event_type="inventory_buildup",
        severity="info",
        title="Inventory Build-up",
        description_template="Inventory increased >20% QoQ while revenue did not grow proportionally.",
        check=lambda facts, metrics, yoy, qoq: (
            lambda inv_pct, rev_pct: (
                inv_pct is not None
                and inv_pct > 20
                and (rev_pct is None or rev_pct < inv_pct * 0.5)
            )
        )(
            _get_qoq_change_pct(qoq, "inventory"),
            _get_qoq_change_pct(qoq, "net_revenue"),
        ),
    ),
    EventRule(
        event_type="cash_flow_quality_warning",
        severity="warning",
        title="Cash Flow Quality Warning",
        description_template="Operating cash flow / net income ratio is below 0.7.",
        check=lambda facts, metrics, yoy, qoq: (
            metrics.get("cf_quality") is not None and metrics["cf_quality"] < 0.7
        ),
    ),
    EventRule(
        event_type="leverage_increase",
        severity="info",
        title="Leverage Increase",
        description_template="Debt-to-equity ratio increased significantly YoY.",
        check=lambda facts, metrics, yoy, qoq: (lambda pct: pct is not None and pct > 10)(
            _get_yoy_change_pct(yoy, "total_liabilities")
        ),
    ),
]


def detect_events(
    facts: dict[str, float],
    metrics: dict[str, float],
    yoy_changes: list[dict],
    qoq_changes: list[dict],
) -> list[dict]:
    """
    Run all event rules and return list of detected event dicts.
    Each dict: {event_type, severity, title, description, related_fields, confidence}
    """
    detected: list[dict] = []
    for rule in EVENT_RULES:
        try:
            triggered = rule.check(facts, metrics, yoy_changes, qoq_changes)
        except Exception as exc:
            logger.debug("Event rule %s check failed: %s", rule.event_type, exc)
            triggered = False

        if not triggered:
            continue

        # Build description with available context
        ctx: dict = {}
        yoy_pct = _get_yoy_change_pct(yoy_changes, "net_revenue")
        if yoy_pct is not None:
            ctx["change_pct"] = yoy_pct
        fcf = metrics.get("free_cash_flow")
        if fcf is not None:
            ctx["value"] = fcf

        try:
            description = rule.description_template.format(**ctx)
        except (KeyError, ValueError):
            description = rule.description_template

        detected.append(
            {
                "event_type": rule.event_type,
                "severity": rule.severity,
                "title": rule.title,
                "description": description,
                "related_fields": [],
                "confidence": 0.85,
            }
        )
        logger.info("Detected event: %s (%s)", rule.event_type, rule.severity)

    return detected

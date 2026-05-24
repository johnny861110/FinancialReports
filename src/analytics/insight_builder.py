"""
Build structured insight cards from financial data.
"""

from __future__ import annotations

import logging

from src.domain.identity import FilingIdentity

logger = logging.getLogger(__name__)

INSIGHT_TYPES = [
    "performance_summary",
    "revenue_growth",
    "margin_change",
    "profitability_change",
    "cash_flow_quality",
    "balance_sheet_strength",
    "working_capital_change",
    "capex_and_investment",
    "debt_and_liquidity",
    "risk_and_commitments",
]


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def _fmt_num(value: float | None, unit: str = "千元") -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f} 十億{unit}"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f} 百萬{unit}"
    return f"{value:.0f} {unit}"


def _get_yoy_pct(yoy: list[dict], field: str) -> float | None:
    for c in yoy:
        if c["field"] == field and c.get("change_pct") is not None:
            return c["change_pct"] / 100  # return as decimal
    return None


def build_performance_summary(
    identity: FilingIdentity,
    facts: dict[str, float],
    metrics: dict[str, float],
    yoy: list[dict],
    qoq: list[dict],
) -> dict | None:
    """Build a top-level performance summary insight card."""
    rev = facts.get("net_revenue")
    ni = facts.get("net_income")
    eps = facts.get("eps_basic")
    gm = metrics.get("gross_margin")
    om = metrics.get("operating_margin")
    rev_yoy = _get_yoy_pct(yoy, "net_revenue")

    if rev is None and ni is None:
        return None

    sentiment = "neutral"
    if rev_yoy is not None:
        if rev_yoy > 0.1:
            sentiment = "positive"
        elif rev_yoy < -0.1:
            sentiment = "negative"

    summary_parts = []
    if rev is not None:
        yoy_str = f"，YoY {rev_yoy * 100:+.1f}%" if rev_yoy is not None else ""
        summary_parts.append(f"營收 {_fmt_num(rev)}{yoy_str}")
    if ni is not None:
        summary_parts.append(f"淨利 {_fmt_num(ni)}")
    if eps is not None:
        summary_parts.append(f"EPS {eps:.2f} 元")
    if gm is not None:
        summary_parts.append(f"毛利率 {gm * 100:.1f}%")

    return {
        "filing_key": identity.filing_key,
        "card_type": "performance_summary",
        "title": f"{identity.stock_code} {identity.year}{identity.quarter} 財務摘要",
        "summary": "；".join(summary_parts) if summary_parts else "財務數據不足",
        "data_points": {
            "net_revenue": rev,
            "net_income": ni,
            "eps_basic": eps,
            "gross_margin": gm,
            "operating_margin": om,
            "revenue_yoy_pct": rev_yoy,
        },
        "sentiment": sentiment,
        "confidence": 0.9,
    }


def build_revenue_growth_insight(
    identity: FilingIdentity,
    facts: dict[str, float],
    yoy: list[dict],
    qoq: list[dict],
) -> dict | None:
    """Build revenue growth insight card."""
    rev = facts.get("net_revenue")
    if rev is None:
        return None

    rev_yoy = _get_yoy_pct(yoy, "net_revenue")
    rev_qoq = _get_yoy_pct(qoq, "net_revenue")

    parts = [f"本期營收 {_fmt_num(rev)}"]
    if rev_yoy is not None:
        parts.append(f"YoY {rev_yoy * 100:+.1f}%")
    if rev_qoq is not None:
        parts.append(f"QoQ {rev_qoq * 100:+.1f}%")

    sentiment = "neutral"
    if rev_yoy is not None:
        sentiment = "positive" if rev_yoy > 0.05 else ("negative" if rev_yoy < -0.05 else "neutral")

    return {
        "filing_key": identity.filing_key,
        "card_type": "revenue_growth",
        "title": "營收成長分析",
        "summary": "、".join(parts),
        "data_points": {
            "net_revenue": rev,
            "yoy_pct": rev_yoy,
            "qoq_pct": rev_qoq,
        },
        "sentiment": sentiment,
        "confidence": 0.85,
    }


def build_margin_insight(
    identity: FilingIdentity,
    metrics: dict[str, float],
    yoy: list[dict],
) -> dict | None:
    """Build margin change insight card."""
    gm = metrics.get("gross_margin")
    om = metrics.get("operating_margin")
    nm = metrics.get("net_margin")

    if gm is None and om is None:
        return None

    gm_yoy = _get_yoy_pct(yoy, "gross_profit")
    parts = []
    if gm is not None:
        parts.append(f"毛利率 {gm * 100:.1f}%")
    if om is not None:
        parts.append(f"營業利益率 {om * 100:.1f}%")
    if nm is not None:
        parts.append(f"淨利率 {nm * 100:.1f}%")
    if gm_yoy is not None:
        direction = "上升" if gm_yoy > 0 else "下降"
        parts.append(f"毛利率 YoY {direction} {abs(gm_yoy) * 100:.1f}pp")

    sentiment = "neutral"
    if gm is not None:
        sentiment = "positive" if gm > 0.3 else ("negative" if gm < 0.1 else "neutral")

    return {
        "filing_key": identity.filing_key,
        "card_type": "margin_change",
        "title": "利潤率分析",
        "summary": "；".join(parts) if parts else "利潤率數據不足",
        "data_points": {
            "gross_margin": gm,
            "operating_margin": om,
            "net_margin": nm,
            "gross_margin_yoy_change": gm_yoy,
        },
        "sentiment": sentiment,
        "confidence": 0.85,
    }


def build_cash_flow_insight(
    identity: FilingIdentity,
    facts: dict[str, float],
    metrics: dict[str, float],
) -> dict | None:
    """Build cash flow quality insight card."""
    ocf = facts.get("operating_cash_flow")
    fcf = metrics.get("free_cash_flow")
    cf_quality = metrics.get("cf_quality")

    if ocf is None:
        return None

    parts = [f"營業現金流 {_fmt_num(ocf)}"]
    if fcf is not None:
        parts.append(f"自由現金流 {_fmt_num(fcf)}")
    if cf_quality is not None:
        parts.append(f"現金流品質比 {cf_quality:.2f}")

    sentiment = "neutral"
    if fcf is not None:
        sentiment = "positive" if fcf > 0 else "negative"
    if cf_quality is not None and cf_quality < 0.7:
        sentiment = "negative"

    return {
        "filing_key": identity.filing_key,
        "card_type": "cash_flow_quality",
        "title": "現金流量品質",
        "summary": "；".join(parts),
        "data_points": {
            "operating_cash_flow": ocf,
            "free_cash_flow": fcf,
            "cf_quality_ratio": cf_quality,
            "capex": facts.get("capex"),
        },
        "sentiment": sentiment,
        "confidence": 0.8,
    }


def build_balance_sheet_insight(
    identity: FilingIdentity,
    facts: dict[str, float],
    metrics: dict[str, float],
) -> dict | None:
    """Build balance sheet strength insight card."""
    assets = facts.get("total_assets")
    equity = facts.get("equity")
    cr = metrics.get("current_ratio")
    dte = metrics.get("debt_to_equity")

    if assets is None and equity is None:
        return None

    parts = []
    if assets is not None:
        parts.append(f"資產總額 {_fmt_num(assets)}")
    if equity is not None:
        parts.append(f"股東權益 {_fmt_num(equity)}")
    if cr is not None:
        parts.append(f"流動比率 {cr:.2f}")
    if dte is not None:
        parts.append(f"負債/權益 {dte:.2f}")

    sentiment = "neutral"
    if cr is not None:
        sentiment = "positive" if cr >= 2.0 else ("negative" if cr < 1.0 else "neutral")

    return {
        "filing_key": identity.filing_key,
        "card_type": "balance_sheet_strength",
        "title": "資產負債表分析",
        "summary": "；".join(parts) if parts else "資產負債數據不足",
        "data_points": {
            "total_assets": assets,
            "equity": equity,
            "current_ratio": cr,
            "debt_to_equity": dte,
        },
        "sentiment": sentiment,
        "confidence": 0.85,
    }


def build_all_insights(
    identity: FilingIdentity,
    facts: dict[str, float],
    metrics: dict[str, float],
    yoy_changes: list[dict],
    qoq_changes: list[dict],
    events: list[dict],
) -> list[dict]:
    """
    Build all insight cards and return list of card dicts.
    Skips cards where required data is missing.
    """
    cards: list[dict] = []
    builders = [
        lambda: build_performance_summary(identity, facts, metrics, yoy_changes, qoq_changes),
        lambda: build_revenue_growth_insight(identity, facts, yoy_changes, qoq_changes),
        lambda: build_margin_insight(identity, metrics, yoy_changes),
        lambda: build_cash_flow_insight(identity, facts, metrics),
        lambda: build_balance_sheet_insight(identity, facts, metrics),
    ]

    for builder in builders:
        try:
            card = builder()
            if card is not None:
                cards.append(card)
        except Exception as exc:
            logger.warning("Insight builder failed: %s", exc)

    # Add event-driven insights
    for event in events:
        if event["severity"] in ("error", "warning"):
            cards.append(
                {
                    "filing_key": identity.filing_key,
                    "card_type": f"event_{event['event_type']}",
                    "title": event["title"],
                    "summary": event["description"],
                    "data_points": {"event_type": event["event_type"]},
                    "sentiment": "negative" if event["severity"] == "error" else "neutral",
                    "confidence": event.get("confidence", 0.8),
                }
            )

    return cards

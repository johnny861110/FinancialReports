"""Tests for analytics: metrics, comparisons, event detection, insights."""

import pytest

from src.analytics.comparisons import compute_changes, get_prior_quarter, get_prior_year
from src.analytics.event_detector import detect_events
from src.analytics.insight_builder import (
    build_all_insights,
    build_cash_flow_insight,
    build_margin_insight,
    build_performance_summary,
    build_revenue_growth_insight,
)
from src.analytics.metrics import compute_all_metrics, compute_fcf, compute_margins, compute_ratios
from src.domain.identity import FilingIdentity
from src.validation.rules import run_all_rules

# ── sample data ───────────────────────────────────────────────────────────────

SAMPLE_FACTS = {
    "net_revenue": 200_000.0,
    "gross_profit": 100_000.0,
    "operating_income": 70_000.0,
    "net_income": 60_000.0,
    "eps_basic": 2.30,
    "total_assets": 500_000.0,
    "total_liabilities": 200_000.0,
    "equity": 300_000.0,
    "current_assets": 150_000.0,
    "current_liabilities": 80_000.0,
    "operating_cash_flow": 80_000.0,
    "capex": -20_000.0,
    "share_capital": 50_000.0,
}

SAMPLE_IDENTITY = FilingIdentity(stock_code="2330", year=2024, quarter="Q2")


class TestMetrics:
    def test_compute_margins(self):
        margins = compute_margins(SAMPLE_FACTS)
        assert margins["gross_margin"] == pytest.approx(0.5)
        assert margins["operating_margin"] == pytest.approx(0.35)
        assert margins["net_margin"] == pytest.approx(0.3)

    def test_compute_margins_zero_revenue(self):
        margins = compute_margins({"net_revenue": 0, "gross_profit": 100})
        assert margins["gross_margin"] is None

    def test_compute_ratios(self):
        ratios = compute_ratios(SAMPLE_FACTS)
        assert ratios["current_ratio"] == pytest.approx(150_000 / 80_000)
        assert ratios["debt_to_equity"] == pytest.approx(200_000 / 300_000)
        assert ratios["roe"] == pytest.approx(60_000 / 300_000)
        assert ratios["roa"] == pytest.approx(60_000 / 500_000)

    def test_compute_fcf(self):
        fcf = compute_fcf(SAMPLE_FACTS)
        # operating_cash_flow - |capex| = 80000 - 20000 = 60000
        assert fcf["free_cash_flow"] == pytest.approx(60_000.0)

    def test_compute_fcf_no_capex(self):
        facts = {"operating_cash_flow": 50_000.0}
        fcf = compute_fcf(facts)
        assert fcf["free_cash_flow"] == 50_000.0

    def test_compute_fcf_no_ocf(self):
        fcf = compute_fcf({})
        assert fcf["free_cash_flow"] is None

    def test_compute_all_metrics(self):
        metrics = compute_all_metrics(SAMPLE_FACTS)
        assert "gross_margin" in metrics
        assert "roe" in metrics
        assert "free_cash_flow" in metrics
        assert "cf_quality" in metrics
        # No None values
        assert all(v is not None for v in metrics.values())

    def test_compute_all_metrics_empty(self):
        metrics = compute_all_metrics({})
        assert isinstance(metrics, dict)


class TestComparisons:
    def test_compute_changes(self):
        current = {"net_revenue": 120.0, "net_income": 20.0}
        prior = {"net_revenue": 100.0, "net_income": 25.0}
        changes = compute_changes(current, prior)
        rev_change = next(c for c in changes if c["field"] == "net_revenue")
        assert rev_change["change_pct"] == pytest.approx(20.0)
        assert rev_change["direction"] == "up"
        ni_change = next(c for c in changes if c["field"] == "net_income")
        assert ni_change["direction"] == "down"

    def test_compute_changes_empty_prior(self):
        current = {"net_revenue": 100.0}
        changes = compute_changes(current, {})
        assert changes == []

    def test_get_prior_quarter_normal(self):
        identity = FilingIdentity("2330", 2024, "Q2")
        prior = get_prior_quarter(identity)
        assert prior.quarter == "Q1"
        assert prior.year == 2024

    def test_get_prior_quarter_wraps(self):
        identity = FilingIdentity("2330", 2024, "Q1")
        prior = get_prior_quarter(identity)
        assert prior.quarter == "Q4"
        assert prior.year == 2023

    def test_get_prior_year(self):
        identity = FilingIdentity("2330", 2024, "Q2")
        prior = get_prior_year(identity)
        assert prior.year == 2023
        assert prior.quarter == "Q2"

    def test_significance_levels(self):
        current = {"revenue": 130.0}
        prior = {"revenue": 100.0}
        changes = compute_changes(current, prior)
        assert changes[0]["significance"] == "large"  # 30% change


class TestEventDetector:
    def test_detect_revenue_growth(self):
        facts = {"net_revenue": 150.0}
        metrics = {}
        yoy = [{"field": "net_revenue", "change_pct": 35.0, "direction": "up"}]
        qoq = []
        events = detect_events(facts, metrics, yoy, qoq)
        types = [e["event_type"] for e in events]
        assert "revenue_growth_acceleration" in types

    def test_detect_revenue_decline(self):
        facts = {}
        metrics = {}
        yoy = [{"field": "net_revenue", "change_pct": -15.0, "direction": "down"}]
        events = detect_events(facts, metrics, yoy, [])
        types = [e["event_type"] for e in events]
        assert "revenue_decline" in types

    def test_detect_fcf_negative(self):
        facts = {}
        metrics = {"free_cash_flow": -5_000.0}
        events = detect_events(facts, metrics, [], [])
        types = [e["event_type"] for e in events]
        assert "fcf_negative" in types

    def test_no_false_positives_good_company(self):
        # Strong company should not trigger most warnings
        metrics = {"free_cash_flow": 50_000.0, "cf_quality": 1.2}
        yoy = [{"field": "net_revenue", "change_pct": 5.0, "direction": "up"}]
        events = detect_events(SAMPLE_FACTS, metrics, yoy, [])
        warning_types = [e["event_type"] for e in events if e["severity"] == "warning"]
        assert "revenue_decline" not in warning_types
        assert "fcf_negative" not in warning_types


class TestInsightBuilder:
    def test_build_performance_summary(self):
        card = build_performance_summary(
            SAMPLE_IDENTITY,
            SAMPLE_FACTS,
            {"gross_margin": 0.5, "operating_margin": 0.35},
            [],
            [],
        )
        assert card is not None
        assert card["card_type"] == "performance_summary"
        assert "2330" in card["title"]

    def test_build_performance_summary_no_data(self):
        card = build_performance_summary(SAMPLE_IDENTITY, {}, {}, [], [])
        assert card is None

    def test_build_revenue_growth(self):
        card = build_revenue_growth_insight(
            SAMPLE_IDENTITY,
            SAMPLE_FACTS,
            [{"field": "net_revenue", "change_pct": 12.0, "direction": "up"}],
            [],
        )
        assert card is not None
        assert card["card_type"] == "revenue_growth"
        assert card["sentiment"] == "positive"

    def test_build_margin_insight(self):
        card = build_margin_insight(
            SAMPLE_IDENTITY,
            {"gross_margin": 0.5, "operating_margin": 0.35, "net_margin": 0.3},
            [],
        )
        assert card is not None
        assert card["card_type"] == "margin_change"

    def test_build_cash_flow_insight(self):
        card = build_cash_flow_insight(
            SAMPLE_IDENTITY,
            SAMPLE_FACTS,
            {"free_cash_flow": 60_000.0, "cf_quality": 1.33},
        )
        assert card is not None
        assert card["card_type"] == "cash_flow_quality"
        assert card["sentiment"] == "positive"

    def test_build_all_insights_returns_list(self):
        metrics = compute_all_metrics(SAMPLE_FACTS)
        cards = build_all_insights(SAMPLE_IDENTITY, SAMPLE_FACTS, metrics, [], [], [])
        assert isinstance(cards, list)
        assert len(cards) >= 2


class TestValidationRules:
    def test_balance_sheet_equation_pass(self):
        facts = {
            "total_assets": 500.0,
            "total_liabilities": 200.0,
            "equity": 300.0,
        }
        results = run_all_rules(facts)
        bs_result = next(r for r in results if r["rule_id"] == "balance_sheet_equation")
        assert bs_result["passed"] is True

    def test_balance_sheet_equation_fail(self):
        facts = {
            "total_assets": 600.0,  # Should be 500
            "total_liabilities": 200.0,
            "equity": 300.0,
        }
        results = run_all_rules(facts)
        bs_result = next(r for r in results if r["rule_id"] == "balance_sheet_equation")
        assert bs_result["passed"] is False

    def test_gross_profit_lte_revenue_pass(self):
        facts = {"net_revenue": 200.0, "gross_profit": 100.0}
        results = run_all_rules(facts)
        gp_result = next(r for r in results if r["rule_id"] == "gross_profit_lte_revenue")
        assert gp_result["passed"] is True

    def test_gross_profit_lte_revenue_fail(self):
        facts = {"net_revenue": 100.0, "gross_profit": 150.0}
        results = run_all_rules(facts)
        gp_result = next(r for r in results if r["rule_id"] == "gross_profit_lte_revenue")
        assert gp_result["passed"] is False

    def test_eps_consistency(self):
        # Positive net income, positive EPS
        facts = {"net_income": 100.0, "eps_basic": 2.5}
        results = run_all_rules(facts)
        eps_result = next(r for r in results if r["rule_id"] == "eps_consistency")
        assert eps_result["passed"] is True

    def test_eps_consistency_mismatch(self):
        # Negative net income, positive EPS — inconsistent
        facts = {"net_income": -100.0, "eps_basic": 2.5}
        results = run_all_rules(facts)
        eps_result = next(r for r in results if r["rule_id"] == "eps_consistency")
        assert eps_result["passed"] is False

    def test_run_all_rules_returns_all(self):
        results = run_all_rules(SAMPLE_FACTS)
        assert len(results) >= 5
        for r in results:
            assert "rule_id" in r
            assert "passed" in r
            assert "severity" in r

"""Tests for domain models and taxonomy."""

import pytest

from src.domain.identity import FilingIdentity
from src.domain.models import Fact, Filing, InsightCard
from src.domain.taxonomy import (
    ALL_CANONICAL,
    FIELD_TO_STATEMENT,
    XBRL_TO_CANONICAL,
)


class TestFilingIdentity:
    def test_period_code(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q1")
        assert identity.period_code == "202401"

    def test_period_code_q4(self):
        identity = FilingIdentity(stock_code="2317", year=2023, quarter="Q4")
        assert identity.period_code == "202304"

    def test_filing_key(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q1")
        assert identity.filing_key == "2330_2024Q1"

    def test_pdf_filename(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q2")
        assert identity.pdf_filename == "202402_2330_AI1.pdf"

    def test_from_filing_key(self):
        identity = FilingIdentity.from_filing_key("2330_2025Q1")
        assert identity.stock_code == "2330"
        assert identity.year == 2025
        assert identity.quarter == "Q1"

    def test_from_filing_key_roundtrip(self):
        original = FilingIdentity(stock_code="2454", year=2024, quarter="Q3")
        restored = FilingIdentity.from_filing_key(original.filing_key)
        assert original == restored

    def test_str(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q1")
        assert str(identity) == "2330_2024Q1"


class TestFilingModel:
    def test_valid_filing(self):
        filing = Filing(
            filing_key="2330_2024Q1",
            stock_code="2330",
            year=2024,
            quarter="Q1",
            status="pending",
        )
        assert filing.filing_key == "2330_2024Q1"
        assert filing.status == "pending"

    def test_invalid_quarter(self):
        with pytest.raises(Exception):
            Filing(filing_key="2330_2024Q5", stock_code="2330", year=2024, quarter="Q5")

    def test_invalid_status(self):
        with pytest.raises(Exception):
            Filing(
                filing_key="2330_2024Q1",
                stock_code="2330",
                year=2024,
                quarter="Q1",
                status="unknown_status",
            )


class TestFactModel:
    def test_valid_fact(self):
        fact = Fact(
            filing_key="2330_2024Q1",
            field="net_revenue",
            value=100_000.0,
            unit="TWD_thousands",
            source_type="xbrl",
        )
        assert fact.value == 100_000.0
        assert fact.confidence == 1.0

    def test_confidence_clamped(self):
        fact = Fact(
            filing_key="2330_2024Q1",
            field="net_revenue",
            value=1.0,
            confidence=1.5,  # should clamp to 1.0
        )
        assert fact.confidence == 1.0

    def test_invalid_source_type(self):
        with pytest.raises(Exception):
            Fact(
                filing_key="2330_2024Q1",
                field="net_revenue",
                value=1.0,
                source_type="invalid_source",
            )


class TestInsightCard:
    def test_insight_card(self):
        card = InsightCard(
            filing_key="2330_2024Q1",
            card_type="performance_summary",
            title="Test Title",
            summary="Test summary",
            data_points={"net_revenue": 100000},
        )
        assert card.card_type == "performance_summary"
        assert card.data_points["net_revenue"] == 100000


class TestTaxonomy:
    def test_xbrl_to_canonical_has_revenue(self):
        assert "Revenue" in XBRL_TO_CANONICAL
        assert XBRL_TO_CANONICAL["Revenue"] == "net_revenue"

    def test_xbrl_to_canonical_has_assets(self):
        assert "Assets" in XBRL_TO_CANONICAL
        assert XBRL_TO_CANONICAL["Assets"] == "total_assets"

    def test_xbrl_to_canonical_eps(self):
        assert XBRL_TO_CANONICAL["BasicEarningsLossPerShare"] == "eps_basic"
        assert XBRL_TO_CANONICAL["EarningsPerShare"] == "eps_basic"

    def test_field_to_statement(self):
        assert FIELD_TO_STATEMENT["net_revenue"] == "income_statement"
        assert FIELD_TO_STATEMENT["total_assets"] == "balance_sheet"
        assert FIELD_TO_STATEMENT["operating_cash_flow"] == "cash_flow"

    def test_all_canonical_not_empty(self):
        assert len(ALL_CANONICAL) > 20

    def test_all_canonical_have_zh(self):
        for field, meta in ALL_CANONICAL.items():
            assert "zh" in meta, f"Field {field} missing zh name"

    def test_all_canonical_have_unit(self):
        for field, meta in ALL_CANONICAL.items():
            assert "unit" in meta, f"Field {field} missing unit"

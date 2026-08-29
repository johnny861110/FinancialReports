"""Tests for the PostgreSQL storage layer."""

import pytest

from src.domain.identity import FilingIdentity
from src.domain.models import Fact, InsightCard
from src.storage.store import FilingStore


@pytest.fixture
def store(database_url):
    """Create a fresh FilingStore in a disposable schema."""
    return FilingStore(database_url)


@pytest.fixture
def identity():
    return FilingIdentity(stock_code="2330", year=2024, quarter="Q1")


@pytest.fixture
def filing_with_company(store, identity):
    """Create a company and filing record, return (filing_id, company_id)."""
    company_id = store.upsert_company("2330", name_zh="台積電")
    filing_id = store.upsert_filing(identity, company_id)
    return filing_id, company_id


class TestCompany:
    def test_upsert_new_company(self, store):
        company_id = store.upsert_company("2330", name_zh="台積電")
        assert company_id is not None
        assert company_id > 0

    def test_upsert_same_company_idempotent(self, store):
        id1 = store.upsert_company("2330", name_zh="台積電")
        id2 = store.upsert_company("2330", name_zh="台積電")
        assert id1 == id2

    def test_upsert_multiple_companies(self, store):
        id1 = store.upsert_company("2330", name_zh="台積電")
        id2 = store.upsert_company("2317", name_zh="鴻海")
        assert id1 != id2


class TestFiling:
    def test_upsert_filing(self, store, identity):
        company_id = store.upsert_company("2330", name_zh="台積電")
        filing_id = store.upsert_filing(identity, company_id)
        assert filing_id is not None and filing_id > 0

    def test_get_filing_id(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        retrieved = store.get_filing_id(identity.filing_key)
        assert retrieved == filing_id

    def test_get_filing_id_missing(self, store):
        assert store.get_filing_id("9999_2099Q4") is None

    def test_get_filing_status_initial(self, store, identity, filing_with_company):
        status = store.get_filing_status(identity.filing_key)
        assert status == "pending"

    def test_update_filing_status(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        store.update_filing_status(filing_id, "ingested")
        assert store.get_filing_status(identity.filing_key) == "ingested"


class TestFacts:
    def test_save_and_retrieve_fact(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        fact = Fact(
            filing_key=identity.filing_key,
            field="net_revenue",
            value=123_456.0,
            unit="TWD_thousands",
            source_type="xbrl",
        )
        fact_id = store.save_fact(filing_id, fact)
        assert fact_id is not None

        retrieved = store.get_facts(identity.filing_key)
        assert len(retrieved) == 1
        assert retrieved[0]["field"] == "net_revenue"
        assert retrieved[0]["value"] == 123_456.0

    def test_get_facts_dict(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        facts = [
            Fact(
                filing_key=identity.filing_key, field="net_revenue", value=100.0, source_type="xbrl"
            ),
            Fact(
                filing_key=identity.filing_key, field="net_income", value=20.0, source_type="xbrl"
            ),
        ]
        store.save_facts_bulk(filing_id, facts)
        d = store.get_facts_dict(identity.filing_key)
        assert d["net_revenue"] == 100.0
        assert d["net_income"] == 20.0

    def test_facts_upsert_same_field_source(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        fact_v1 = Fact(
            filing_key=identity.filing_key, field="net_revenue", value=100.0, source_type="xbrl"
        )
        fact_v2 = Fact(
            filing_key=identity.filing_key, field="net_revenue", value=200.0, source_type="xbrl"
        )
        store.save_fact(filing_id, fact_v1)
        store.save_fact(filing_id, fact_v2)
        facts = store.get_facts(identity.filing_key)
        # Should have only one fact (upserted)
        xbrl_facts = [
            f for f in facts if f["source_type"] == "xbrl" and f["field"] == "net_revenue"
        ]
        assert len(xbrl_facts) == 1
        assert xbrl_facts[0]["value"] == 200.0

    def test_facts_prefer_xbrl_in_dict(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        xbrl_fact = Fact(
            filing_key=identity.filing_key, field="net_revenue", value=100.0, source_type="xbrl"
        )
        pdf_fact = Fact(
            filing_key=identity.filing_key, field="net_revenue", value=99.0, source_type="pdf_table"
        )
        store.save_fact(filing_id, xbrl_fact)
        store.save_fact(filing_id, pdf_fact)
        d = store.get_facts_dict(identity.filing_key)
        assert d["net_revenue"] == 100.0  # XBRL preferred


class TestMetrics:
    def test_save_and_retrieve_metric(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        store.save_metric(filing_id, "gross_margin", 0.53, formula="gross_profit/net_revenue")
        metrics = store.get_metrics(identity.filing_key)
        assert len(metrics) == 1
        assert metrics[0]["metric_name"] == "gross_margin"
        assert metrics[0]["value"] == pytest.approx(0.53)


class TestInsightCards:
    def test_save_and_retrieve_insight_card(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        card = InsightCard(
            filing_key=identity.filing_key,
            card_type="performance_summary",
            title="Test Title",
            summary="Test summary",
            data_points={"net_revenue": 100000},
            sentiment="positive",
        )
        card_id = store.save_insight_card(filing_id, card)
        assert card_id is not None

        cards = store.get_insight_cards(identity.filing_key)
        assert len(cards) == 1
        assert cards[0]["card_type"] == "performance_summary"
        assert cards[0]["data_points"]["net_revenue"] == 100000


class TestValidation:
    def test_save_validation_result(self, store, identity, filing_with_company):
        filing_id, _ = filing_with_company
        store.save_validation_result(filing_id, "balance_sheet_equation", True, "error", "OK")
        results = store.get_validation_results(identity.filing_key)
        assert len(results) == 1
        assert results[0]["rule_name"] == "balance_sheet_equation"
        assert results[0]["passed"] == 1


class TestPipelineLog:
    def test_log_pipeline_run(self, store, identity, filing_with_company):
        store.log_pipeline_run(identity.filing_key, "ingest", "started")
        store.log_pipeline_run(identity.filing_key, "ingest", "completed")
        # Should not raise


class TestIdempotentExtraction:
    """Re-extracting a document must replace its text, not append another copy."""

    def test_clear_document_text_removes_pages_sections_and_chunks(self, store, identity):
        company_id = store.upsert_company("2330")
        filing_id = store.upsert_filing(identity, company_id)
        doc_id = store.save_source_doc(filing_id, "pdf", "/tmp/f.pdf")

        store.save_page(doc_id, 1, "page text", False)
        section_id = store.save_section(doc_id, "risk", "風險", 1, 2, "內容")
        store.save_chunk(doc_id, section_id, 1, 0, "chunk content")

        store.clear_document_text(doc_id)

        assert store.get_chunks(identity.filing_key) == []
        with store.conn() as conn:
            from sqlalchemy import text

            for table in ("document_pages", "document_sections", "document_chunks"):
                remaining = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE doc_id=:d"), {"d": doc_id}
                ).scalar_one()
                assert remaining == 0, f"{table} still holds rows"

    def test_clearing_also_removes_dependent_embeddings(self, store, identity):
        """chunk_embeddings references chunks, so it must go first."""
        from sqlalchemy import text

        company_id = store.upsert_company("2330")
        filing_id = store.upsert_filing(identity, company_id)
        doc_id = store.save_source_doc(filing_id, "pdf", "/tmp/f.pdf")
        chunk_id = store.save_chunk(doc_id, None, 1, 0, "embedded chunk")

        with store.conn() as conn:
            conn.execute(
                text(
                    "INSERT INTO chunk_embeddings(chunk_id, model_name, embedding)"
                    " VALUES(:c, 'test', CAST(:v AS vector))"
                ),
                {"c": chunk_id, "v": str([0.0] * 768)},
            )

        store.clear_document_text(doc_id)

        with store.conn() as conn:
            assert conn.execute(text("SELECT COUNT(*) FROM chunk_embeddings")).scalar_one() == 0

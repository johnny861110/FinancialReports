"""Question-directed and section-filtered chunk retrieval.

These tests never load an embedding model. sentence-transformers lives in the
optional `vector` extra and CI installs only the dev group, so the pgvector
query path is exercised by inserting known unit vectors directly: that covers
the SQL, the ordering and the contract without a 400 MB model download, and it
keeps the assertions deterministic.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.agent.embedding import EMBEDDING_DIM
from src.api.app import create_app
from src.domain.identity import FilingIdentity

PERIOD = "2025Q1"
STOCK = "2330"


def _unit_vector(index: int) -> list[float]:
    """A one-hot vector, so cosine similarity between distinct indices is 0."""
    vector = [0.0] * EMBEDDING_DIM
    vector[index] = 1.0
    return vector


@pytest.fixture
def retrieval_client(database_url):
    """A filing with three chunks across two sections, ready to embed."""
    app = create_app(database_url)
    with TestClient(app) as client:
        store = client.app.state.store
        identity = FilingIdentity(stock_code=STOCK, year=2025, quarter="Q1")
        company_id = store.upsert_company(STOCK, name_zh="台積電")
        filing_id = store.upsert_filing(identity, company_id)
        store.update_filing_status(filing_id, "insight_ready")
        doc_id = store.save_source_doc(
            filing_id, "pdf", "/internal/secret/path.pdf", "https://example.com/f.pdf", 1234
        )

        risk_section = store.save_section(doc_id, "risk", "風險因素", 10, 12, "風險章節")
        policy_section = store.save_section(
            doc_id, "accounting_policy", "會計政策", 20, 22, "政策章節"
        )

        chunks = {
            # (label, section, page, importance, content)
            "risk_high": (risk_section, 10, 0.9, "本公司面臨匯率波動風險" + "詳述" * 800),
            "risk_low": (risk_section, 11, 0.1, "其他風險說明"),
            "policy": (policy_section, 20, 0.5, "本期會計政策變更如下"),
        }
        ids = {}
        for label, (section, page, importance, content) in chunks.items():
            ids[label] = store.save_chunk(
                doc_id, section, page, 0, content, importance_score=importance
            )

        client.chunk_ids = ids  # type: ignore[attr-defined]
        client.store = store  # type: ignore[attr-defined]
        yield client


def _embed(store, chunk_id: int, index: int) -> None:
    with store.conn() as conn:
        conn.execute(
            text(
                "INSERT INTO chunk_embeddings(chunk_id, model_name, embedding)"
                " VALUES(:cid, 'test-model', CAST(:vec AS vector))"
                " ON CONFLICT (chunk_id) DO UPDATE SET embedding=EXCLUDED.embedding"
            ),
            {"cid": chunk_id, "vec": str(_unit_vector(index))},
        )


def _context(client, **params):
    return client.get(f"/v1/filings/{STOCK}/{PERIOD}/context", params=params)


def test_sections_filter_narrows_to_requested_sections(retrieval_client):
    response = _context(retrieval_client, sections=["accounting_policy"], evidence_limit=10)

    assert response.status_code == 200
    chunks = response.json()["evidence_chunks"]
    assert {c["section_type"] for c in chunks} == {"accounting_policy"}


def test_multiple_sections_are_unioned(retrieval_client):
    response = _context(retrieval_client, sections=["risk", "accounting_policy"], evidence_limit=10)

    assert response.status_code == 200
    assert {c["section_type"] for c in response.json()["evidence_chunks"]} == {
        "risk",
        "accounting_policy",
    }


def test_unknown_section_is_rejected_rather_than_returning_nothing(retrieval_client):
    response = _context(retrieval_client, sections=["not_a_section"])

    assert response.status_code == 422
    detail = response.json()["error"]
    assert detail["code"] == "unknown_sections"
    assert detail["details"]["sections"] == ["not_a_section"]


def test_without_a_question_chunks_come_back_in_importance_order(retrieval_client):
    response = _context(retrieval_client, evidence_limit=10)

    chunks = response.json()["evidence_chunks"]
    scores = [c["importance_score"] for c in chunks]
    assert scores == sorted(scores, reverse=True)
    assert all(c["retrieval_score"] is None for c in chunks)


def test_question_reorders_results_by_vector_similarity(retrieval_client):
    """The chunk matching the question outranks a higher-importance chunk."""
    ids = retrieval_client.chunk_ids
    store = retrieval_client.store
    _embed(store, ids["risk_high"], 0)
    _embed(store, ids["risk_low"], 1)
    _embed(store, ids["policy"], 2)

    # A question embedding is not computable without the model, so drive the
    # same code path by pointing the query vector at the policy chunk.
    from src.api import app as app_module

    original = app_module.encode_question
    app_module.encode_question = lambda q: _unit_vector(2)
    try:
        response = _context(retrieval_client, question="會計政策變更", evidence_limit=3)
    finally:
        app_module.encode_question = original

    chunks = response.json()["evidence_chunks"]
    assert chunks[0]["chunk_id"] == ids["policy"], "vector match must outrank importance"
    assert chunks[0]["retrieval_score"] == pytest.approx(1.0)
    assert chunks[1]["retrieval_score"] < chunks[0]["retrieval_score"]


def test_question_falls_back_to_importance_when_filing_has_no_embeddings(retrieval_client):
    """A filing that was never embedded still answers, rather than returning nothing."""
    from src.api import app as app_module

    original = app_module.encode_question
    app_module.encode_question = lambda q: _unit_vector(2)
    try:
        response = _context(retrieval_client, question="會計政策變更", evidence_limit=3)
    finally:
        app_module.encode_question = original

    chunks = response.json()["evidence_chunks"]
    assert chunks, "fallback must still return evidence"
    assert all(c["retrieval_score"] is None for c in chunks)
    scores = [c["importance_score"] for c in chunks]
    assert scores == sorted(scores, reverse=True)


def test_chunk_payload_carries_citation_fields_and_never_the_local_path(retrieval_client):
    response = _context(retrieval_client, evidence_limit=1)

    chunk = response.json()["evidence_chunks"][0]
    assert chunk["source_url"] == "https://example.com/f.pdf"
    assert chunk["doc_id"] is not None
    assert chunk["page_number"] is not None
    assert chunk["section_type"] is not None
    # The document's local filesystem path must never reach a consumer.
    assert "/internal/secret/path.pdf" not in response.text


def test_long_chunk_content_is_capped_and_flagged(retrieval_client):
    from src.api.service import MAX_CHUNK_CHARS

    response = _context(retrieval_client, sections=["risk"], evidence_limit=10)

    long_chunk = next(c for c in response.json()["evidence_chunks"] if c["truncated"])
    assert len(long_chunk["content"]) == MAX_CHUNK_CHARS


def test_evidence_limit_bounds_are_enforced(retrieval_client):
    assert _context(retrieval_client, evidence_limit=0).json()["evidence_chunks"] == []
    assert _context(retrieval_client, evidence_limit=51).status_code == 422
    assert _context(retrieval_client, evidence_limit=50).status_code == 200


def test_overlong_question_is_rejected(retrieval_client):
    assert _context(retrieval_client, question="漲" * 501).status_code == 422


def test_duplicate_content_is_returned_once(retrieval_client):
    """The ingestion pipeline stores the same text repeatedly.

    94% of rows in the current data set are redundant copies, so without
    deduplication the caller's bounded chunk budget is spent returning one
    passage over and over. Distinct chunk ids with identical content must
    collapse to a single result.
    """
    store = retrieval_client.store
    ids = retrieval_client.chunk_ids
    with store.conn() as conn:
        original = conn.execute(
            text(
                "SELECT doc_id, section_id, page_number, content, importance_score"
                " FROM document_chunks WHERE id=:i"
            ),
            {"i": ids["policy"]},
        ).fetchone()
    # A second chunk carrying byte-identical content, as the pipeline produces.
    duplicate_id = store.save_chunk(
        original[0], original[1], original[2], 1, original[3], importance_score=original[4]
    )
    assert duplicate_id != ids["policy"]

    response = _context(retrieval_client, sections=["accounting_policy"], evidence_limit=10)

    chunks = response.json()["evidence_chunks"]
    contents = [c["content"] for c in chunks]
    assert len(contents) == len(set(contents)), "duplicate content must collapse"
    assert len([c for c in chunks if c["chunk_id"] in (ids["policy"], duplicate_id)]) == 1

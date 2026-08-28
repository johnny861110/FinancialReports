-- Financial Insight Engine Database Schema
-- PostgreSQL. Foreign keys are enforced natively; no PRAGMA equivalents needed.

-- Companies master table
CREATE TABLE IF NOT EXISTS companies (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stock_code TEXT        NOT NULL UNIQUE,
    name_zh    TEXT,
    name_en    TEXT,
    industry   TEXT,
    market     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Quarterly filings
CREATE TABLE IF NOT EXISTS filings (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_key    TEXT        NOT NULL UNIQUE,
    company_id    INTEGER     NOT NULL REFERENCES companies(id),
    year          INTEGER     NOT NULL,
    quarter       TEXT        NOT NULL,
    status        TEXT        NOT NULL DEFAULT 'pending',
    quality_score DOUBLE PRECISION,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Source documents (XBRL, iXBRL, PDF)
CREATE TABLE IF NOT EXISTS source_documents (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id     INTEGER     NOT NULL REFERENCES filings(id),
    doc_type      TEXT        NOT NULL,   -- 'xbrl' | 'ixbrl' | 'pdf'
    local_path    TEXT,
    url           TEXT,
    file_size     INTEGER,
    checksum      TEXT,
    downloaded_at TIMESTAMPTZ,
    parse_status  TEXT        NOT NULL DEFAULT 'pending'
);

-- Canonical financial facts
CREATE TABLE IF NOT EXISTS financial_facts (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id    INTEGER          NOT NULL REFERENCES filings(id),
    field        TEXT             NOT NULL,
    value        DOUBLE PRECISION NOT NULL,
    unit         TEXT             NOT NULL DEFAULT 'TWD_thousands',
    period_start TEXT,
    period_end   TEXT,
    period_type  TEXT             NOT NULL DEFAULT 'duration',
    source_type  TEXT             NOT NULL DEFAULT 'xbrl',
    confidence   DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    xbrl_tag     TEXT,
    created_at   TIMESTAMPTZ      NOT NULL DEFAULT now(),
    UNIQUE(filing_id, field, source_type)
);

-- Evidence linking facts to source locations
CREATE TABLE IF NOT EXISTS fact_evidence (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fact_id           INTEGER NOT NULL REFERENCES financial_facts(id),
    doc_id            INTEGER REFERENCES source_documents(id),
    page_number       INTEGER,
    section_title     TEXT,
    raw_text          TEXT,
    extraction_method TEXT    NOT NULL DEFAULT 'xbrl'
);

-- Full text content per page
CREATE TABLE IF NOT EXISTS document_pages (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doc_id       INTEGER NOT NULL REFERENCES source_documents(id),
    page_number  INTEGER NOT NULL,
    text_content TEXT,
    char_count   INTEGER NOT NULL DEFAULT 0,
    has_tables   BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(doc_id, page_number)
);

-- Document sections (income statement, balance sheet, etc.)
CREATE TABLE IF NOT EXISTS document_sections (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doc_id       INTEGER NOT NULL REFERENCES source_documents(id),
    section_type TEXT    NOT NULL,
    title        TEXT,
    page_start   INTEGER NOT NULL,
    page_end     INTEGER NOT NULL,
    content      TEXT
);

-- RAG chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    doc_id            INTEGER          NOT NULL REFERENCES source_documents(id),
    section_id        INTEGER          REFERENCES document_sections(id),
    page_number       INTEGER          NOT NULL,
    chunk_index       INTEGER          NOT NULL DEFAULT 0,
    content           TEXT             NOT NULL,
    char_offset_start INTEGER,
    char_offset_end   INTEGER,
    contains_numbers  BOOLEAN          NOT NULL DEFAULT FALSE,
    contains_table    BOOLEAN          NOT NULL DEFAULT FALSE,
    importance_score  DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    created_at        TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- Vector embeddings for chunks.
-- Populated offline by `fr embed` (needs the `vector` extra); retrieval falls
-- back to section filtering and importance when a filing has none.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id   INTEGER PRIMARY KEY REFERENCES document_chunks(id) ON DELETE CASCADE,
    model_name TEXT         NOT NULL,
    embedding  VECTOR(768)  NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Text summaries
CREATE TABLE IF NOT EXISTS text_summaries (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id    INTEGER     NOT NULL REFERENCES filings(id),
    summary_type TEXT        NOT NULL,
    content      TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Computed financial metrics (margins, ratios, etc.)
CREATE TABLE IF NOT EXISTS financial_metrics (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id   INTEGER          NOT NULL REFERENCES filings(id),
    metric_name TEXT             NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    formula     TEXT,
    inputs_json TEXT,
    confidence  DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT now(),
    UNIQUE(filing_id, metric_name)
);

-- Period-over-period comparisons
CREATE TABLE IF NOT EXISTS period_comparisons (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id         INTEGER          NOT NULL REFERENCES filings(id),
    compare_filing_id INTEGER          REFERENCES filings(id),
    field             TEXT             NOT NULL,
    compare_type      TEXT             NOT NULL,   -- 'yoy' | 'qoq'
    current_value     DOUBLE PRECISION NOT NULL,
    prior_value       DOUBLE PRECISION NOT NULL,
    change_abs        DOUBLE PRECISION,
    change_pct        DOUBLE PRECISION,
    direction         TEXT,                        -- 'up' | 'down' | 'flat'
    significance      TEXT,                        -- 'large' | 'moderate' | 'small'
    interpretation    TEXT
);

-- Detected financial events
CREATE TABLE IF NOT EXISTS detected_events (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id           INTEGER          NOT NULL REFERENCES filings(id),
    event_type          TEXT             NOT NULL,
    severity            TEXT             NOT NULL DEFAULT 'info',
    title               TEXT,
    description         TEXT,
    related_fields_json TEXT,
    confidence          DOUBLE PRECISION NOT NULL DEFAULT 0.9,
    created_at          TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- Insight cards for agent consumption
CREATE TABLE IF NOT EXISTS insight_cards (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id    INTEGER          NOT NULL REFERENCES filings(id),
    card_type    TEXT             NOT NULL,
    title        TEXT             NOT NULL,
    summary      TEXT             NOT NULL,
    data_points  TEXT,                        -- JSON blob
    sentiment    TEXT,                        -- 'positive' | 'negative' | 'neutral'
    confidence   DOUBLE PRECISION NOT NULL DEFAULT 0.8,
    generated_at TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- Evidence linking insight cards to source material
CREATE TABLE IF NOT EXISTS insight_evidence (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    card_id         INTEGER          NOT NULL REFERENCES insight_cards(id),
    evidence_type   TEXT             NOT NULL,   -- 'fact' | 'chunk' | 'metric'
    ref_id          INTEGER,
    quote           TEXT,
    page_number     INTEGER,
    section_title   TEXT,
    relevance_score DOUBLE PRECISION NOT NULL DEFAULT 0.5
);

-- Validation results
CREATE TABLE IF NOT EXISTS validation_results (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_id  INTEGER     NOT NULL REFERENCES filings(id),
    rule_name  TEXT        NOT NULL,
    passed     BOOLEAN     NOT NULL DEFAULT TRUE,
    severity   TEXT        NOT NULL DEFAULT 'info',
    message    TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pipeline execution log
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filing_key    TEXT        NOT NULL,
    stage         TEXT        NOT NULL,
    status        TEXT        NOT NULL,   -- 'started' | 'completed' | 'failed' | 'skipped'
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    error_message TEXT
);

-- Indexes on foreign keys and lookup columns.
-- SQLite got away without these at this data size; Postgres does not index
-- foreign keys automatically, and the read path joins chunks -> documents ->
-- filings over 342k rows on every context request.
CREATE INDEX IF NOT EXISTS idx_filings_company        ON filings(company_id);
CREATE INDEX IF NOT EXISTS idx_source_docs_filing     ON source_documents(filing_id);
CREATE INDEX IF NOT EXISTS idx_facts_filing           ON financial_facts(filing_id);
CREATE INDEX IF NOT EXISTS idx_fact_evidence_fact     ON fact_evidence(fact_id);
CREATE INDEX IF NOT EXISTS idx_fact_evidence_doc      ON fact_evidence(doc_id);
CREATE INDEX IF NOT EXISTS idx_pages_doc              ON document_pages(doc_id);
CREATE INDEX IF NOT EXISTS idx_sections_doc           ON document_sections(doc_id);
CREATE INDEX IF NOT EXISTS idx_sections_type          ON document_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_chunks_doc             ON document_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_section         ON document_chunks(section_id);
CREATE INDEX IF NOT EXISTS idx_chunks_importance      ON document_chunks(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_filing       ON text_summaries(filing_id);
CREATE INDEX IF NOT EXISTS idx_metrics_filing         ON financial_metrics(filing_id);
CREATE INDEX IF NOT EXISTS idx_comparisons_filing     ON period_comparisons(filing_id);
CREATE INDEX IF NOT EXISTS idx_events_filing          ON detected_events(filing_id);
CREATE INDEX IF NOT EXISTS idx_cards_filing           ON insight_cards(filing_id);
CREATE INDEX IF NOT EXISTS idx_insight_evidence_card  ON insight_evidence(card_id);
CREATE INDEX IF NOT EXISTS idx_validation_filing      ON validation_results(filing_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_filing_key    ON pipeline_runs(filing_key);

-- Approximate nearest-neighbour index for question-directed retrieval.
-- Cosine distance, matching the normalised embeddings `fr embed` writes.
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
    ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);

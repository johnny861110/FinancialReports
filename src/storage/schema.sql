-- Financial Insight Engine Database Schema
-- SQLite with WAL mode for concurrent access

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Companies master table
CREATE TABLE IF NOT EXISTS companies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT    NOT NULL UNIQUE,
    name_zh    TEXT,
    name_en    TEXT,
    industry   TEXT,
    market     TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Quarterly filings
CREATE TABLE IF NOT EXISTS filings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_key  TEXT    NOT NULL UNIQUE,
    company_id  INTEGER NOT NULL REFERENCES companies(id),
    year        INTEGER NOT NULL,
    quarter     TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending',
    quality_score REAL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Source documents (XBRL, iXBRL, PDF)
CREATE TABLE IF NOT EXISTS source_documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id     INTEGER NOT NULL REFERENCES filings(id),
    doc_type      TEXT    NOT NULL,   -- 'xbrl' | 'ixbrl' | 'pdf'
    local_path    TEXT,
    url           TEXT,
    file_size     INTEGER,
    checksum      TEXT,
    downloaded_at TEXT,
    parse_status  TEXT    NOT NULL DEFAULT 'pending'
);

-- Canonical financial facts
CREATE TABLE IF NOT EXISTS financial_facts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id    INTEGER NOT NULL REFERENCES filings(id),
    field        TEXT    NOT NULL,
    value        REAL    NOT NULL,
    unit         TEXT    NOT NULL DEFAULT 'TWD_thousands',
    period_start TEXT,
    period_end   TEXT,
    period_type  TEXT    NOT NULL DEFAULT 'duration',
    source_type  TEXT    NOT NULL DEFAULT 'xbrl',
    confidence   REAL    NOT NULL DEFAULT 1.0,
    xbrl_tag     TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(filing_id, field, source_type)
);

-- Evidence linking facts to source locations
CREATE TABLE IF NOT EXISTS fact_evidence (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id           INTEGER NOT NULL REFERENCES financial_facts(id),
    doc_id            INTEGER REFERENCES source_documents(id),
    page_number       INTEGER,
    section_title     TEXT,
    raw_text          TEXT,
    extraction_method TEXT    NOT NULL DEFAULT 'xbrl'
);

-- Full text content per page
CREATE TABLE IF NOT EXISTS document_pages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id       INTEGER NOT NULL REFERENCES source_documents(id),
    page_number  INTEGER NOT NULL,
    text_content TEXT,
    char_count   INTEGER NOT NULL DEFAULT 0,
    has_tables   INTEGER NOT NULL DEFAULT 0,
    UNIQUE(doc_id, page_number)
);

-- Document sections (income statement, balance sheet, etc.)
CREATE TABLE IF NOT EXISTS document_sections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id       INTEGER NOT NULL REFERENCES source_documents(id),
    section_type TEXT    NOT NULL,
    title        TEXT,
    page_start   INTEGER NOT NULL,
    page_end     INTEGER NOT NULL,
    content      TEXT
);

-- RAG chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id              INTEGER NOT NULL REFERENCES source_documents(id),
    section_id          INTEGER REFERENCES document_sections(id),
    page_number         INTEGER NOT NULL,
    chunk_index         INTEGER NOT NULL DEFAULT 0,
    content             TEXT    NOT NULL,
    char_offset_start   INTEGER,
    char_offset_end     INTEGER,
    contains_numbers    INTEGER NOT NULL DEFAULT 0,
    contains_table      INTEGER NOT NULL DEFAULT 0,
    importance_score    REAL    NOT NULL DEFAULT 0.5,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Vector embeddings for chunks (optional)
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id   INTEGER PRIMARY KEY REFERENCES document_chunks(id),
    model_name TEXT    NOT NULL,
    embedding  BLOB    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Text summaries
CREATE TABLE IF NOT EXISTS text_summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id    INTEGER NOT NULL REFERENCES filings(id),
    summary_type TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Computed financial metrics (margins, ratios, etc.)
CREATE TABLE IF NOT EXISTS financial_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id   INTEGER NOT NULL REFERENCES filings(id),
    metric_name TEXT    NOT NULL,
    value       REAL    NOT NULL,
    formula     TEXT,
    inputs_json TEXT,
    confidence  REAL    NOT NULL DEFAULT 1.0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(filing_id, metric_name)
);

-- Period-over-period comparisons
CREATE TABLE IF NOT EXISTS period_comparisons (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id        INTEGER NOT NULL REFERENCES filings(id),
    compare_filing_id INTEGER REFERENCES filings(id),
    field            TEXT    NOT NULL,
    compare_type     TEXT    NOT NULL,   -- 'yoy' | 'qoq'
    current_value    REAL    NOT NULL,
    prior_value      REAL    NOT NULL,
    change_abs       REAL,
    change_pct       REAL,
    direction        TEXT,               -- 'up' | 'down' | 'flat'
    significance     TEXT,               -- 'large' | 'moderate' | 'small'
    interpretation   TEXT
);

-- Detected financial events
CREATE TABLE IF NOT EXISTS detected_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id           INTEGER NOT NULL REFERENCES filings(id),
    event_type          TEXT    NOT NULL,
    severity            TEXT    NOT NULL DEFAULT 'info',
    title               TEXT,
    description         TEXT,
    related_fields_json TEXT,
    confidence          REAL    NOT NULL DEFAULT 0.9,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Insight cards for agent consumption
CREATE TABLE IF NOT EXISTS insight_cards (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id    INTEGER NOT NULL REFERENCES filings(id),
    card_type    TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    summary      TEXT    NOT NULL,
    data_points  TEXT,               -- JSON blob
    sentiment    TEXT,               -- 'positive' | 'negative' | 'neutral'
    confidence   REAL    NOT NULL DEFAULT 0.8,
    generated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Evidence linking insight cards to source material
CREATE TABLE IF NOT EXISTS insight_evidence (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id        INTEGER NOT NULL REFERENCES insight_cards(id),
    evidence_type  TEXT    NOT NULL,   -- 'fact' | 'chunk' | 'metric'
    ref_id         INTEGER,
    quote          TEXT,
    page_number    INTEGER,
    section_title  TEXT,
    relevance_score REAL   NOT NULL DEFAULT 0.5
);

-- Validation results
CREATE TABLE IF NOT EXISTS validation_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id  INTEGER NOT NULL REFERENCES filings(id),
    rule_name  TEXT    NOT NULL,
    passed     INTEGER NOT NULL DEFAULT 1,
    severity   TEXT    NOT NULL DEFAULT 'info',
    message    TEXT,
    checked_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Pipeline execution log
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_key    TEXT    NOT NULL,
    stage         TEXT    NOT NULL,
    status        TEXT    NOT NULL,   -- 'started' | 'completed' | 'failed' | 'skipped'
    started_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    finished_at   TEXT,
    error_message TEXT
);

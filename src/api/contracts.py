"""Transport contracts for FinancialReports API v1.

These models are intentionally separate from persistence and pipeline models so
the external contract can evolve without coupling consumers to database details.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataState(str, Enum):
    PRESENT = "present"
    MISSING = "missing"
    NULL = "null"
    NOT_APPLICABLE = "not_applicable"
    PROVIDER_FAILURE = "provider_failure"


class FilingStatus(str, Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    INSIGHT_READY = "insight_ready"
    FAILED = "failed"


class ReadinessStatus(str, Enum):
    READY = "ready"
    PROCESSING = "processing"
    STALE = "stale"


class SourceType(str, Enum):
    XBRL = "xbrl"
    IXBRL = "ixbrl"
    FINMIND = "finmind"
    PDF_TABLE = "pdf_table"
    PDF_TEXT = "pdf_text"
    COMPUTED = "computed"


class PeriodType(str, Enum):
    DURATION = "duration"
    INSTANT = "instant"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Identity(ContractModel):
    stock_code: str
    period: str = Field(pattern=r"^\d{4}Q[1-4]$")
    filing_key: str
    company_name: str
    company_name_zh: str | None = None
    company_name_en: str | None = None
    industry: str | None = None
    market: str | None = None


class Freshness(ContractModel):
    state: Literal["current", "stale", "unknown"]
    updated_at: datetime | None = None
    is_stale: bool
    latest_source_at: datetime | None = None
    stale_after_seconds: int = 86400


class ValidationFailure(ContractModel):
    rule_name: str
    passed: Literal[False] = False
    severity: Literal["error", "warning", "info"]
    message: str | None = None
    checked_at: datetime | None = None


class Quality(ContractModel):
    score: float | None = Field(default=None, ge=0, le=1)
    state: DataState
    missing_fields: list[str] = Field(default_factory=list)
    validation_failures: list[ValidationFailure] = Field(default_factory=list)
    validation_total: int = Field(ge=0)
    validation_failed: int = Field(ge=0)
    structured_source_coverage: float | None = Field(default=None, ge=0, le=1)


class SnapshotValues(ContractModel):
    net_revenue: float | None = None
    gross_profit: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps_basic: float | None = None
    eps: float | None = Field(default=None, description="Compatibility alias of eps_basic")
    total_assets: float | None = None
    total_liabilities: float | None = None
    equity: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    net_interest_income: float | None = None
    net_non_interest_income: float | None = None
    loan_loss_provisions: float | None = None


class Evidence(ContractModel):
    fact_id: int | None = None
    field: str | None = None
    source_document_id: int | None = None
    doc_id: int | None = None
    source_type: str
    page_number: int | None = None
    section_title: str | None = None
    raw_text: str | None = None
    excerpt: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    extraction_method: str | None = None
    source_url: str | None = None
    checksum: str | None = None


class Fact(ContractModel):
    id: int
    field: str
    value: float
    unit: str
    statement: str
    period_start: str | None = None
    period_end: str | None = None
    period_type: PeriodType
    source_type: SourceType
    confidence: float = Field(ge=0, le=1)
    xbrl_tag: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class FieldAvailability(ContractModel):
    field: str
    statement: str
    unit: str
    state: DataState
    reason: str | None = None


class Metric(ContractModel):
    name: str
    value: float
    unit: str = Field(description="ratio is decimal-scaled; percent is 100-scaled")
    formula: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)


class Event(ContractModel):
    event_type: str
    severity: Literal["error", "warning", "info"]
    title: str | None = None
    description: str
    related_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class ValidationResult(ContractModel):
    rule_name: str
    passed: bool
    severity: Literal["error", "warning", "info"]
    message: str | None = None
    checked_at: datetime | None = None


class Comparison(ContractModel):
    field: str
    compare_type: Literal["yoy", "qoq"]
    compare_period: str | None = None
    current_value: float
    prior_value: float
    change_abs: float | None = None
    change_pct: float | None = Field(default=None, description="100-scaled percent")
    direction: Literal["up", "down", "flat"] | None = None
    significance: Literal["large", "moderate", "small"] | None = None
    interpretation: str | None = None


class InsightCard(ContractModel):
    id: int
    card_type: str
    title: str
    summary: str
    data_points: dict[str, Any] = Field(default_factory=dict)
    sentiment: Literal["positive", "negative", "neutral"] | None = None
    confidence: float = Field(ge=0, le=1)
    generated_at: datetime | None = None


class SourceDocument(ContractModel):
    id: int
    doc_type: Literal["xbrl", "ixbrl", "pdf", "finmind"]
    url: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    checksum: str | None = None
    downloaded_at: datetime | None = None
    parse_status: str


class PipelineRun(ContractModel):
    stage: str
    status: Literal["started", "completed", "failed", "skipped"]
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None


class FilingEnvelope(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    identity: Identity
    status: ReadinessStatus
    pipeline_status: FilingStatus
    freshness: Freshness
    quality: Quality
    snapshot: SnapshotValues
    metrics: dict[str, Any] = Field(
        description="Backward-compatible metric name to value/metadata mapping"
    )
    metric_records: list[Metric]
    events: list[Event]
    evidence: list[Evidence]
    facts: list[Fact]
    field_availability: list[FieldAvailability]
    validation: list[ValidationResult]
    comparisons: list[Comparison]
    insight_cards: list[InsightCard]
    source_documents: list[SourceDocument]
    pipeline_state: list[PipelineRun]


class EvidenceChunk(ContractModel):
    """One citable excerpt of filing text.

    Carries what a consumer needs in order to cite it: a stable id, the source
    document with its checksum and public URL, and the position within it. The
    document's local filesystem path is deliberately never exposed.
    """

    chunk_id: int
    doc_id: int
    page_number: int | None = None
    section_type: str | None = None
    section_title: str | None = None
    content: str
    truncated: bool = False
    checksum: str | None = None
    source_url: str | None = None
    importance_score: float | None = None
    # Cosine similarity to the question when one was given and the filing has
    # embeddings; None means the chunk was selected by importance instead.
    retrieval_score: float | None = None


class RetrievalMode(str, Enum):
    """How `evidence_chunks` were ordered."""

    SEMANTIC = "semantic"
    """Ranked by cosine distance between the question and chunk embeddings."""

    IMPORTANCE = "importance"
    """Ranked by the chunker's importance_score; the question did not affect it."""


class RetrievalInfo(ContractModel):
    """Whether evidence selection did what the caller asked for.

    A question can go unused for reasons the caller cannot otherwise detect --
    the embedding model missing from the deployment, or the filing never having
    been through `fr embed`. Both previously produced a well-formed evidence
    list, ordered by importance, that was indistinguishable from a semantic
    search result apart from a null `retrieval_score` the caller would have had
    to notice. `state` reports it explicitly, using the same DataState
    vocabulary the snapshot path already applies per field.
    """

    mode: RetrievalMode
    state: DataState
    """PRESENT when the question ranked the results. NOT_APPLICABLE when no
    question was asked. PROVIDER_FAILURE when a question was asked but the
    embedding model was unavailable. MISSING when the filing has no
    embeddings."""

    detail: str | None = None
    """Human-readable reason, present whenever `state` is not PRESENT."""


class ContextEnvelope(FilingEnvelope):
    evidence_chunks: list[EvidenceChunk] = Field(default_factory=list)
    retrieval: RetrievalInfo


class StockSummary(ContractModel):
    stock_code: str
    name_zh: str | None = None
    name_en: str | None = None
    industry: str | None = None
    market: str | None = None
    periods_count: int = Field(ge=0)


class Pagination(ContractModel):
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)


class StocksResponse(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    items: list[StockSummary]
    stocks: list[StockSummary] = Field(description="Compatibility alias of items")
    pagination: Pagination


class PeriodSummary(ContractModel):
    period: str
    status: FilingStatus
    quality_score: float | None = Field(default=None, ge=0, le=1)
    updated_at: datetime


class PeriodsResponse(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    stock_code: str
    items: list[PeriodSummary]
    periods: list[str] = Field(description="Compatibility list of YYYYQn periods")
    pagination: Pagination


class RefreshResponse(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    job_id: str
    status: JobStatus
    identity: Identity


class JobResponse(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    identity: Identity
    result: dict[str, Any] | None = None
    error: str | None = None
    data_state: DataState | None = None


class BatchQueryItem(ContractModel):
    stock_code: str = Field(pattern=r"^[A-Za-z0-9]{1,12}$")
    period: str = Field(pattern=r"^\d{4}Q[1-4]$")
    fields: list[str] | None = Field(default=None, max_length=40)


class BatchQueryRequest(ContractModel):
    items: list[BatchQueryItem] = Field(min_length=1, max_length=100)


class BatchResult(ContractModel):
    identity: Identity
    data: FilingEnvelope | None = None
    error: ErrorDetail | None = None


class BatchQueryResponse(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    items: list[BatchResult]


class ErrorDetail(ContractModel):
    code: str
    message: str
    data_state: DataState
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    error: ErrorDetail


class HealthResponse(ContractModel):
    status: Literal["ok", "ready", "not_ready"]
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION


class FieldDefinition(ContractModel):
    name: str
    statement: str
    unit: str
    label_zh: str
    period_type: PeriodType
    xbrl_tags: list[str]


class CapabilitiesResponse(ContractModel):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    api_version: Literal["v1"] = "v1"
    endpoints: list[str]
    limits: dict[str, int]
    units: dict[str, str]
    data_states: dict[str, str]
    fields: list[FieldDefinition]


BatchResult.model_rebuild()

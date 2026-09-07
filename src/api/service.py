"""Contract assembly and semantic mapping for API v1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from src.api.contracts import (
    Comparison,
    ContextEnvelope,
    DataState,
    Event,
    Evidence,
    EvidenceChunk,
    Fact,
    FieldAvailability,
    FilingEnvelope,
    FilingStatus,
    Freshness,
    Identity,
    InsightCard,
    Metric,
    PeriodType,
    PipelineRun,
    Quality,
    ReadinessStatus,
    RetrievalInfo,
    RetrievalMode,
    SnapshotValues,
    SourceDocument,
    SourceType,
    ValidationFailure,
    ValidationResult,
)
from src.domain.taxonomy import ALL_CANONICAL, FIELD_TO_STATEMENT

STRUCTURED_SOURCES = {"xbrl", "ixbrl", "finmind"}
SOURCE_PRIORITY = {
    "xbrl": 0,
    "ixbrl": 1,
    "finmind": 2,
    "pdf_table": 3,
    "pdf_text": 4,
    "computed": 5,
}
METRIC_UNITS = {
    "gross_margin": "ratio",
    "operating_margin": "ratio",
    "net_margin": "ratio",
    "roe": "ratio",
    "roa": "ratio",
    "rd_intensity": "ratio",
    "current_ratio": "ratio",
    "debt_to_equity": "ratio",
    "cf_quality": "ratio",
    "book_value_per_share": "TWD_per_share",
    "free_cash_flow": "TWD_thousands",
}
SNAPSHOT_FIELDS = {
    "net_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "eps_basic",
    "total_assets",
    "total_liabilities",
    "equity",
    "operating_cash_flow",
    "free_cash_flow",
    "net_interest_income",
    "net_non_interest_income",
    "loan_loss_provisions",
}
BANK_NOT_APPLICABLE = {"gross_profit", "current_assets", "current_liabilities", "inventory"}
BANK_ONLY = {"net_interest_income", "net_non_interest_income", "loan_loss_provisions"}


class APIProblem(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        data_state: DataState,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.data_state = data_state
        self.retryable = retryable
        self.details = details or {}


def parse_period(period: str) -> tuple[int, str]:
    if len(period) != 6 or period[4] != "Q" or not period[:4].isdigit() or period[5] not in "1234":
        raise APIProblem(422, "invalid_period", "period must use YYYYQn", DataState.MISSING)
    year = int(period[:4])
    if year < 1990 or year > datetime.now().year + 1:
        raise APIProblem(
            422, "invalid_period", "period year is outside supported bounds", DataState.MISSING
        )
    return year, period[4:]


def ensure_fields(fields: list[str] | None) -> list[str] | None:
    if fields is None:
        return None
    unknown = sorted(set(fields) - set(ALL_CANONICAL))
    if unknown:
        raise APIProblem(
            422,
            "unknown_fields",
            "one or more canonical fields are unknown",
            DataState.MISSING,
            details={"fields": unknown},
        )
    return list(dict.fromkeys(fields))


def retrieval_info(
    question: str | None, question_embedding: list[float] | None, semantic: bool
) -> RetrievalInfo:
    """Describe how evidence was selected, so a degraded path is visible.

    `semantic` must come from APIRepository.uses_semantic_ranking so that what
    is reported is the branch that actually ran.
    """
    if semantic:
        return RetrievalInfo(mode=RetrievalMode.SEMANTIC, state=DataState.PRESENT)
    if not question:
        return RetrievalInfo(
            mode=RetrievalMode.IMPORTANCE,
            state=DataState.NOT_APPLICABLE,
            detail="no question was supplied; chunks are ordered by importance",
        )
    if question_embedding is None:
        return RetrievalInfo(
            mode=RetrievalMode.IMPORTANCE,
            state=DataState.PROVIDER_FAILURE,
            detail=(
                "the embedding model is unavailable, so the question did not affect "
                "ranking; chunks are ordered by importance"
            ),
        )
    return RetrievalInfo(
        mode=RetrievalMode.IMPORTANCE,
        state=DataState.MISSING,
        detail=(
            "this filing has no chunk embeddings, so the question did not affect "
            "ranking; chunks are ordered by importance. Run `fr embed` for it"
        ),
    )


def build_envelope(
    bundle: dict[str, Any],
    fields: list[str] | None = None,
    chunks: list[dict[str, Any]] | None = None,
    retrieval: RetrievalInfo | None = None,
    corpus_version: str | None = None,
) -> FilingEnvelope | ContextEnvelope:
    filing = bundle["filing"]
    pipeline_status = FilingStatus(filing["status"])

    # Checked before the provider-failure branch below, which would otherwise
    # claim this. A filing with no source document fails its pipeline by
    # design, but 503 says the producer is unavailable and is marked
    # retryable -- so a consumer backing off and retrying reports the whole
    # service as down over one permanently empty filing, burns its retry
    # budget on something that can never succeed, and loses the ability to
    # tell this apart from a real outage. It is a conflict with the filing's
    # own state, and it will not resolve on its own.
    if not bundle["source_documents"]:
        raise APIProblem(
            409,
            "filing_has_no_source_documents",
            "filing exists but no source document was ever obtained for it",
            DataState.MISSING,
            retryable=False,
            details={"pipeline_status": pipeline_status.value},
        )

    latest_failed = any(item["status"] == "failed" for item in bundle["pipeline_state"][-4:])
    if pipeline_status is FilingStatus.FAILED or latest_failed:
        raise APIProblem(
            503,
            "provider_failure",
            "the latest provider or pipeline operation failed",
            DataState.PROVIDER_FAILURE,
            retryable=True,
            details={"pipeline_status": pipeline_status.value},
        )
    if pipeline_status not in {FilingStatus.VALIDATED, FilingStatus.INSIGHT_READY}:
        raise APIProblem(
            409,
            "filing_not_ready",
            "filing exists but is not ready for snapshot consumption",
            DataState.MISSING,
            retryable=True,
            details={"pipeline_status": pipeline_status.value},
        )

    selected = set(fields) if fields else set(ALL_CANONICAL)
    raw_facts = [item for item in bundle["facts"] if item["field"] in selected]
    facts = [
        Fact(
            **{
                **item,
                "statement": FIELD_TO_STATEMENT.get(item["field"], "unknown"),
                "period_type": PeriodType(item["period_type"]),
                "source_type": SourceType(item["source_type"]),
                "evidence": [Evidence(**evidence) for evidence in item["evidence"]],
            }
        )
        for item in raw_facts
    ]
    preferred: dict[str, Fact] = {}
    for fact in facts:
        current = preferred.get(fact.field)
        if (
            current is None
            or SOURCE_PRIORITY[fact.source_type.value] < SOURCE_PRIORITY[current.source_type.value]
        ):
            preferred[fact.field] = fact

    metrics = [
        Metric(
            name=item["name"],
            value=item["value"],
            unit=METRIC_UNITS.get(item["name"], "unknown"),
            formula=item["formula"],
            inputs=item["inputs"],
            confidence=item["confidence"],
        )
        for item in bundle["metrics"]
    ]
    metric_map = {item.name: item.value for item in metrics}

    # One resolution of "what value does this envelope actually carry for each
    # canonical field", read by everything downstream.
    #
    # It used to be two: the snapshot was facts plus a special case that
    # back-filled free_cash_flow from the metrics table, while availability and
    # missing_fields were derived from facts alone. So the same response
    # published free_cash_flow = 348,213,466 and declared it `missing`, on all
    # 69 filings -- a document contradicting itself, and a consumer duly told
    # its users the figure was unavailable while holding it. Resolving once
    # makes that class of contradiction unrepresentable rather than fixing the
    # one field: any future computed canonical field is covered automatically.
    resolved: dict[str, tuple[float, SourceType]] = {
        name: (fact.value, fact.source_type) for name, fact in preferred.items()
    }
    for name in ALL_CANONICAL:
        if name not in resolved and name in metric_map:
            # Derived rather than supplied, which is what `computed` is for.
            resolved[name] = (metric_map[name], SourceType.COMPUTED)

    snapshot_data = {
        name: resolved[name][0] if name in resolved else None for name in SNAPSHOT_FIELDS
    }
    snapshot_data["eps"] = snapshot_data["eps_basic"]

    updated_at = _as_datetime(filing["updated_at"])
    latest_source = max(
        (
            _as_datetime(item["downloaded_at"])
            for item in bundle["source_documents"]
            if item["downloaded_at"]
        ),
        default=None,
    )
    age = (datetime.now(timezone.utc) - _aware(updated_at)).total_seconds()
    freshness_state: Literal["stale", "current"] = "stale" if age > 86400 else "current"
    freshness = Freshness(
        state=freshness_state,
        updated_at=updated_at,
        is_stale=freshness_state == "stale",
        latest_source_at=latest_source,
    )
    readiness = ReadinessStatus.STALE if freshness_state == "stale" else ReadinessStatus.READY

    validation = [
        ValidationResult(**{**item, "passed": bool(item["passed"])})
        for item in bundle["validation"]
    ]
    structured = {fact.field for fact in facts if fact.source_type.value in STRUCTURED_SOURCES}
    quality_score = filing["quality_score"]
    is_bank = filing["stock_code"].startswith("28")
    not_applicable = BANK_NOT_APPLICABLE if is_bank else BANK_ONLY
    missing_fields = sorted(
        name for name in selected if name not in resolved and name not in not_applicable
    )
    validation_failures = [
        ValidationFailure(
            rule_name=item.rule_name,
            severity=item.severity,
            message=item.message,
            checked_at=item.checked_at,
        )
        for item in validation
        if not item.passed
    ]
    quality = Quality(
        score=quality_score,
        state=DataState.NULL if quality_score is None else DataState.PRESENT,
        missing_fields=missing_fields,
        validation_failures=validation_failures,
        validation_total=len(validation),
        validation_failed=sum(not item.passed for item in validation),
        structured_source_coverage=len(structured) / len(ALL_CANONICAL),
    )

    failed_state = DataState.PROVIDER_FAILURE if latest_failed else DataState.MISSING
    availability = []
    for name in sorted(selected):
        state = DataState.PRESENT if name in resolved else failed_state
        reason = None
        if (is_bank and name in BANK_NOT_APPLICABLE) or (not is_bank and name in BANK_ONLY):
            state = DataState.NOT_APPLICABLE
            reason = "field is not applicable to this company sector"
        elif state is DataState.MISSING:
            reason = "expected field was not supplied by available sources"
        elif resolved[name][1] is SourceType.COMPUTED:
            reason = "derived from other canonical fields rather than supplied by a source"
        availability.append(
            FieldAvailability(
                field=name,
                statement=FIELD_TO_STATEMENT[name],
                unit=ALL_CANONICAL[name]["unit"],
                state=state,
                reason=reason,
            )
        )

    identity = Identity(
        stock_code=filing["stock_code"],
        period=f"{filing['year']}{filing['quarter']}",
        filing_key=filing["filing_key"],
        company_name=filing["name_zh"] or filing["name_en"] or filing["stock_code"],
        company_name_zh=filing["name_zh"],
        company_name_en=filing["name_en"],
        industry=filing["industry"],
        market=filing["market"],
    )
    base: dict[str, Any] = {
        "identity": identity,
        "status": readiness,
        "pipeline_status": pipeline_status,
        "freshness": freshness,
        "quality": quality,
        "snapshot": SnapshotValues(**snapshot_data),
        "metrics": metric_map,
        "metric_records": metrics,
        "events": [Event(**{**item, "title": item["title"] or None}) for item in bundle["events"]],
        "evidence": [Evidence(**item) for item in bundle["evidence"]],
        "facts": facts,
        "field_availability": availability,
        "validation": validation,
        "comparisons": [Comparison(**item) for item in bundle["comparisons"]],
        "insight_cards": [InsightCard(**item) for item in bundle["insight_cards"]],
        "source_documents": [SourceDocument(**item) for item in bundle["source_documents"]],
        "pipeline_state": [PipelineRun(**item) for item in bundle["pipeline_state"]],
    }
    if chunks is not None:
        if retrieval is None:  # pragma: no cover - defensive
            raise ValueError("a context envelope must report how retrieval ran")
        return ContextEnvelope(
            **base,
            evidence_chunks=[_evidence_chunk(c) for c in chunks],
            retrieval=retrieval,
            corpus_version=corpus_version,
        )
    return FilingEnvelope(**base)


# Per-chunk content cap. evidence_limit bounds how many chunks come back, but
# without a size cap a caller could still pull unbounded filing text into an
# LLM prompt.
MAX_CHUNK_CHARS = 1200


def _evidence_chunk(row: dict[str, Any]) -> EvidenceChunk:
    content = row.get("content") or ""
    return EvidenceChunk(
        chunk_id=row["id"],
        doc_id=row["doc_id"],
        page_number=row.get("page_number"),
        section_type=row.get("section_type"),
        section_title=row.get("section_title"),
        content=content[:MAX_CHUNK_CHARS],
        truncated=len(content) > MAX_CHUNK_CHARS,
        checksum=row.get("checksum"),
        source_url=row.get("source_url"),
        importance_score=row.get("importance_score"),
        retrieval_score=row.get("retrieval_score"),
    )


def _as_datetime(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

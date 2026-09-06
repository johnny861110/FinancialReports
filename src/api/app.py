"""FastAPI application exposing FinancialReports contract v1."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from src.agent.embedding import encode_question
from src.api.contracts import (
    SCHEMA_VERSION,
    BatchQueryRequest,
    BatchQueryResponse,
    BatchResult,
    CapabilitiesResponse,
    ContextEnvelope,
    DataState,
    ErrorDetail,
    ErrorResponse,
    FieldDefinition,
    FilingEnvelope,
    HealthResponse,
    Identity,
    JobResponse,
    Pagination,
    PeriodsResponse,
    PeriodSummary,
    PeriodType,
    RefreshResponse,
    StocksResponse,
    StockSummary,
)
from src.api.jobs import JobRegistry
from src.api.repository import APIRepository
from src.api.service import (
    APIProblem,
    build_envelope,
    ensure_fields,
    parse_period,
    retrieval_info,
)
from src.domain.identity import FilingIdentity
from src.domain.taxonomy import ALL_CANONICAL, CANONICAL_BALANCE, FIELD_TO_STATEMENT
from src.pipeline.run import run_pipeline_async
from src.storage.store import FilingStore, resolve_database_url

logger = logging.getLogger(__name__)

# Loading a cold embedding model pulls ~400MB. Bound the wait so a slow or
# unreachable model costs one request its semantic ranking instead of the
# service its availability.
_EMBED_TIMEOUT_SECONDS = 20.0

RefreshRunner = Callable[[FilingIdentity, FilingStore, Path], Awaitable[dict[str, Any]]]


def _repository(request: Request) -> APIRepository:
    return request.app.state.repository


Repo = Annotated[APIRepository, Depends(_repository)]


async def _default_refresh_runner(
    identity: FilingIdentity, store: FilingStore, output_dir: Path
) -> dict[str, Any]:
    result = await run_pipeline_async(identity, store, output_dir, force=True)
    failed = [stage for stage, state in result.items() if state.get("status") == "failed"]
    if failed:
        raise RuntimeError(f"pipeline stages failed: {', '.join(failed)}")
    return result


def create_app(
    database_url: str | None = None,
    *,
    refresh_runner: RefreshRunner | None = None,
) -> FastAPI:
    resolved_url = resolve_database_url(database_url)
    output_dir = Path(os.getenv("FR_OUTPUT_DIR", "data/raw"))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        store = FilingStore(resolved_url)
        app.state.store = store
        app.state.repository = APIRepository(store)
        app.state.jobs = JobRegistry()
        app.state.refresh_runner = refresh_runner or _default_refresh_runner
        app.state.output_dir = output_dir
        yield
        store.engine.dispose()

    app = FastAPI(
        title="FinancialReports API",
        version=SCHEMA_VERSION,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    @app.exception_handler(APIProblem)
    async def api_problem_handler(request: Request, exc: APIProblem) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    data_state=exc.data_state,
                    retryable=exc.retryable,
                    details=exc.details,
                )
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="validation_error",
                    message="request validation failed",
                    data_state=DataState.MISSING,
                    details={"errors": exc.errors()},
                )
            ).model_dump(mode="json"),
        )

    @app.get("/health/live", response_model=HealthResponse, tags=["health"])
    async def health_live() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/health/ready", response_model=HealthResponse, tags=["health"])
    async def health_ready(repo: Repo) -> HealthResponse | JSONResponse:
        if repo.ready():
            return HealthResponse(status="ready")
        return JSONResponse(
            status_code=503, content=HealthResponse(status="not_ready").model_dump()
        )

    @app.get("/v1/capabilities", response_model=CapabilitiesResponse, tags=["discovery"])
    async def capabilities() -> CapabilitiesResponse:
        return _capabilities()

    @app.get("/v1/schema", tags=["discovery"])
    async def schema_discovery() -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "openapi_url": "/openapi.json",
            "capabilities": _capabilities().model_dump(mode="json"),
            "models": {
                "snapshot": FilingEnvelope.model_json_schema(),
                "context": ContextEnvelope.model_json_schema(),
                "error": ErrorResponse.model_json_schema(),
            },
        }

    @app.get("/v1/stocks", response_model=StocksResponse, tags=["filings"])
    async def list_stocks(
        repo: Repo,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=100000)] = 0,
        query: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        industry: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    ) -> StocksResponse:
        rows, total = repo.list_stocks(limit, offset, query, industry)
        stocks = [StockSummary(**row) for row in rows]
        return StocksResponse(
            items=stocks,
            stocks=stocks,
            pagination=Pagination(limit=limit, offset=offset, total=total),
        )

    @app.get("/v1/stocks/{stock_code}/periods", response_model=PeriodsResponse, tags=["filings"])
    async def list_periods(
        stock_code: str,
        repo: Repo,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    ) -> PeriodsResponse:
        try:
            rows, total = repo.list_periods(stock_code, limit, offset)
        except LookupError as exc:
            raise APIProblem(
                404, "stock_not_found", "stock was not found", DataState.MISSING
            ) from exc
        items = [PeriodSummary(**row) for row in rows]
        return PeriodsResponse(
            stock_code=stock_code,
            items=items,
            periods=[item.period for item in items],
            pagination=Pagination(limit=limit, offset=offset, total=total),
        )

    @app.get(
        "/v1/filings/{stock_code}/{period}/snapshot",
        response_model=FilingEnvelope,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
        tags=["filings"],
    )
    async def snapshot(
        stock_code: str,
        period: str,
        repo: Repo,
        fields: Annotated[list[str] | None, Query()] = None,
    ) -> FilingEnvelope:
        selected = _validate_query(stock_code, period, fields)
        return _get_envelope(repo, stock_code, period, selected)

    @app.get(
        "/v1/filings/{stock_code}/{period}/context",
        response_model=ContextEnvelope,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
        tags=["filings"],
    )
    async def context(
        stock_code: str,
        period: str,
        repo: Repo,
        fields: Annotated[list[str] | None, Query()] = None,
        evidence_limit: Annotated[int, Query(ge=0, le=50)] = 10,
        question: Annotated[str | None, Query(max_length=500)] = None,
        sections: Annotated[list[str] | None, Query()] = None,
    ) -> ContextEnvelope:
        selected = _validate_query(stock_code, period, fields)
        validated_sections = _validate_sections(repo, sections)
        bundle = _get_bundle(repo, stock_code, period)
        # None when no question was asked, or when the embedding model is not
        # installed -- retrieval then falls back to importance ordering rather
        # than failing the request. Whichever happens is reported back on the
        # envelope's `retrieval` field, so a caller never has to infer from a
        # null retrieval_score that its question was ignored.
        filing_key = bundle["filing"]["filing_key"]
        question_embedding = await _embed_question(question) if question else None
        semantic = repo.uses_semantic_ranking(filing_key, question_embedding)
        chunks = repo.get_chunks(
            filing_key,
            evidence_limit,
            sections=validated_sections,
            question_embedding=question_embedding,
        )
        result = build_envelope(
            bundle,
            selected,
            chunks,
            retrieval=retrieval_info(question, question_embedding, semantic),
            corpus_version=repo.corpus_version(filing_key),
        )
        assert isinstance(result, ContextEnvelope)
        return result

    @app.post(
        "/v1/filings/{stock_code}/{period}/refresh",
        response_model=RefreshResponse,
        status_code=202,
        tags=["jobs"],
    )
    async def refresh(
        stock_code: str, period: str, background_tasks: BackgroundTasks, request: Request
    ) -> RefreshResponse:
        year, quarter = _validate_identity(stock_code, period)
        identity = Identity(
            stock_code=stock_code,
            period=period,
            filing_key=f"{stock_code}_{period}",
            company_name=stock_code,
        )
        job = request.app.state.jobs.create(identity)
        background_tasks.add_task(
            _execute_refresh,
            request.app,
            job.job_id,
            FilingIdentity(stock_code=stock_code, year=year, quarter=quarter),
        )
        return RefreshResponse(job_id=job.job_id, status=job.status, identity=identity)

    @app.get("/v1/jobs/{job_id}", response_model=JobResponse, tags=["jobs"])
    async def get_job(job_id: str, request: Request) -> JobResponse:
        job = request.app.state.jobs.get(job_id)
        if job is None:
            raise APIProblem(404, "job_not_found", "job was not found", DataState.MISSING)
        return job

    @app.post("/v1/batch/filings/query", response_model=BatchQueryResponse, tags=["batch"])
    async def batch_query(payload: BatchQueryRequest, repo: Repo) -> BatchQueryResponse:
        results: list[BatchResult] = []
        for item in payload.items:
            identity = Identity(
                stock_code=item.stock_code,
                period=item.period,
                filing_key=f"{item.stock_code}_{item.period}",
                company_name=item.stock_code,
            )
            try:
                selected = _validate_query(item.stock_code, item.period, item.fields)
                data = _get_envelope(repo, item.stock_code, item.period, selected)
                results.append(BatchResult(identity=identity, data=data))
            except APIProblem as exc:
                results.append(
                    BatchResult(
                        identity=identity,
                        error=ErrorDetail(
                            code=exc.code,
                            message=exc.message,
                            data_state=exc.data_state,
                            retryable=exc.retryable,
                            details=exc.details,
                        ),
                    )
                )
        return BatchQueryResponse(items=results)

    return app


async def _execute_refresh(app: FastAPI, job_id: str, identity: FilingIdentity) -> None:
    jobs: JobRegistry = app.state.jobs
    jobs.running(job_id)
    try:
        result = await app.state.refresh_runner(identity, app.state.store, app.state.output_dir)
        jobs.succeeded(job_id, result)
    except Exception as exc:
        jobs.failed(job_id, str(exc))


def _validate_identity(stock_code: str, period: str) -> tuple[int, str]:
    if not stock_code.isalnum() or len(stock_code) > 12:
        raise APIProblem(
            422, "invalid_stock_code", "stock_code must be alphanumeric", DataState.MISSING
        )
    return parse_period(period)


def _validate_query(stock_code: str, period: str, fields: list[str] | None) -> list[str] | None:
    _validate_identity(stock_code, period)
    if fields is not None and len(fields) > 40:
        raise APIProblem(422, "too_many_fields", "at most 40 fields are allowed", DataState.MISSING)
    return ensure_fields(fields)


async def _embed_question(question: str) -> list[float] | None:
    """Embed off the event loop, and give up rather than hang.

    encode_question is synchronous and, on a cold cache, downloads and loads a
    ~400MB model. Called directly from this async handler it blocked the event
    loop: a single question-bearing request against a stalled download took the
    whole service down -- every endpoint, the healthcheck included -- for nine
    hours, with nothing in the logs explaining it. The process stayed up and
    looked fine from the outside.

    Degrading one request into importance ordering is reported honestly on the
    envelope's `retrieval` field, so this failure is now visible rather than
    silent and total.
    """
    try:
        return await asyncio.wait_for(
            run_in_threadpool(encode_question, question), _EMBED_TIMEOUT_SECONDS
        )
    except (TimeoutError, asyncio.TimeoutError):
        logger.warning(
            "Embedding the question took longer than %.0fs, so retrieval fell back to "
            "importance ordering. The model is usually cold or being downloaded; "
            "mount a warm HuggingFace cache into the container to avoid it.",
            _EMBED_TIMEOUT_SECONDS,
        )
        return None
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Embedding the question failed (%s); falling back", exc)
        return None


def _validate_sections(repo: APIRepository, sections: list[str] | None) -> list[str] | None:
    """Reject unknown section types rather than silently returning nothing."""
    if not sections:
        return None
    known = set(repo.known_section_types())
    unknown = sorted(set(sections) - known)
    if unknown:
        raise APIProblem(
            422,
            "unknown_sections",
            "one or more section types are unknown",
            DataState.MISSING,
            details={"sections": unknown, "known": sorted(known)},
        )
    return list(dict.fromkeys(sections))


def _get_bundle(repo: APIRepository, stock_code: str, period: str) -> dict[str, Any]:
    bundle = repo.get_filing(stock_code, period)
    if bundle is None:
        raise APIProblem(404, "filing_not_found", "filing was not found", DataState.MISSING)
    return bundle


def _get_envelope(
    repo: APIRepository, stock_code: str, period: str, fields: list[str] | None
) -> FilingEnvelope:
    result = build_envelope(_get_bundle(repo, stock_code, period), fields)
    assert isinstance(result, FilingEnvelope) and not isinstance(result, ContextEnvelope)
    return result


def _capabilities() -> CapabilitiesResponse:
    fields = [
        FieldDefinition(
            name=name,
            statement=FIELD_TO_STATEMENT[name],
            unit=meta["unit"],
            label_zh=meta["zh"],
            period_type=PeriodType.INSTANT if name in CANONICAL_BALANCE else PeriodType.DURATION,
            xbrl_tags=meta.get("xbrl_tags", []),
        )
        for name, meta in ALL_CANONICAL.items()
    ]
    return CapabilitiesResponse(
        endpoints=[
            "GET /v1/filings/{stock_code}/{period}/snapshot",
            "GET /v1/filings/{stock_code}/{period}/context",
            "GET /v1/stocks/{stock_code}/periods",
            "GET /v1/stocks",
            "POST /v1/filings/{stock_code}/{period}/refresh",
            "GET /v1/jobs/{job_id}",
            "POST /v1/batch/filings/query",
        ],
        limits={
            "stocks_page": 100,
            "periods_page": 100,
            "fields": 40,
            "batch_items": 100,
            "evidence_chunks": 50,
        },
        units={
            "ratio": "decimal-scaled ratio; 0.25 means 25%",
            "percent": "100-scaled percentage; 25 means 25%",
            "TWD_thousands": "thousands of New Taiwan dollars",
            "TWD_per_share": "New Taiwan dollars per share",
            "unknown": "metric unit is not registered; consumer must not infer percent semantics",
        },
        data_states={
            "present": "a value was supplied and validated by the contract",
            "missing": "an applicable value was not supplied",
            "null": "the property is known but its value is unknown",
            "not_applicable": "the field does not apply to the company sector or statement",
            "provider_failure": "retrieval or processing failed; retry may succeed",
        },
        fields=fields,
    )


app = create_app()

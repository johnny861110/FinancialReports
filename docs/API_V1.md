# FinancialReports API v1

The API is a versioned network contract for typed consumers. Consumers do not
read this repository's SQLite database or local files. The committed
`docs/openapi-v1.json` is the baseline for generated clients and cross-repository
contract tests.

## Run locally

```bash
FR_DB_PATH=data/financial.db uv run uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

- OpenAPI: `GET /openapi.json`
- Swagger UI: `GET /docs`
- Liveness/readiness: `GET /health/live`, `GET /health/ready`
- Discovery: `GET /v1/capabilities`, `GET /v1/schema`

Regenerate the committed contract after an intentional API change:

```bash
uv run python -m src.api.export_openapi
```

## Consumer-compatible endpoints

- `GET /v1/filings/{stock_code}/{period}/snapshot`
- `GET /v1/filings/{stock_code}/{period}/context`
- `GET /v1/stocks/{stock_code}/periods`
- `GET /v1/stocks`
- `POST /v1/filings/{stock_code}/{period}/refresh`
- `GET /v1/jobs/{job_id}`

`period` always uses `YYYYQn`. A successful snapshot has `status=ready|stale`
and includes enough data to construct a FinancialSnapshot. A filing that has
not reached `validated` returns 409; provider or pipeline failure returns 503;
missing filings return 404. Refresh returns 202 with a job id.

Compatibility fields are preserved alongside richer sections:

- `identity.company_name` resolves `name_zh`, then `name_en`, then stock code.
- `snapshot.eps` aliases `snapshot.eps_basic`.
- `metrics` remains a name-to-value mapping; `metric_records` contains typed
  unit/formula/input/confidence records.
- stock and period responses expose both `items` and top-level `stocks` or
  `periods`.
- `status` is consumer readiness; `pipeline_status` preserves the source
  pipeline lifecycle.

## Units and absence semantics

- `ratio` is decimal-scaled: `0.25` means 25%.
- `percent` is 100-scaled: `25` means 25%.
- `TWD_thousands` is thousands of New Taiwan dollars.
- `TWD_per_share` is New Taiwan dollars per share.
- `present`: a value is supplied.
- `missing`: an applicable value was not supplied.
- `null`: the property is known but the value is unknown.
- `not_applicable`: the field does not apply to the company sector.
- `provider_failure`: retrieval or processing failed and may be retried.

Each canonical fact includes unit, period bounds/type, source, confidence,
XBRL tag, and evidence. The response also includes full field availability,
validation records, comparisons, insight cards, source-document provenance
(without server-local paths), and pipeline state.

## Filtering, pagination, and batch bounds

Stock and period pages are bounded to 100 records. Snapshot/context field
filters accept at most 40 known canonical fields. Context evidence chunks are
bounded to 50. `POST /v1/batch/filings/query` accepts 1–100 identities and
returns a success or typed error for each item.

## Release status

API v1 and the FinMind/bank taxonomy baseline are merged into `main`. The
committed OpenAPI document and `tests/test_api_contract.py` are the compatibility
boundary for Financial Agent and other typed consumers. Feature branches used
during the rollout have been removed.

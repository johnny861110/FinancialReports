# FinancialReports API v1

The API is a versioned network contract for typed consumers. Consumers do not
read this repository's PostgreSQL database or local files. The committed
`docs/openapi-v1.json` is the baseline for generated clients and cross-repository
contract tests.

## Run locally

```bash
uv run uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8000
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
and includes enough data to construct a FinancialSnapshot. Missing filings
return 404. Refresh returns 202 with a job id.

Two distinct 409s and one 503, and the difference matters to a retry policy:

| Status | `error.code` | `retryable` | Meaning |
|---|---|---|---|
| 409 | `filing_not_ready` | `true` | The filing exists but has not reached `validated`. Running the pipeline will resolve it. |
| 409 | `filing_has_no_source_documents` | **`false`** | No source document was ever obtained for this filing. It will **never** resolve on retry; treat it as a permanent data gap for that filing, not as an error. |
| 503 | `provider_failure` | `true` | The producer or its upstream genuinely failed. |
| 500 | `internal_error` | `true` | An unhandled producer error. The cause is in the producer's logs, deliberately not in the response. |

Every failure, 500 included, uses the `ErrorResponse` shape — there is no path
that returns a bare `{"detail": ...}`.

Refresh job failures follow the same rule: `JobResponse.error` carries the
message for errors this project raises deliberately (they are written to be
read), and for anything else only the exception type plus a pointer to the
logs, because third-party error text can carry connection strings and internal
paths.

`filing_has_no_source_documents` applies to **both** `/snapshot` and
`/context`. It exists because this case used to answer 503, so a consumer
retrying on `>= 500` burned its budget on a permanent condition and then
reported the whole producer as unavailable over a single empty filing — which
also made a real outage indistinguishable from an empty one. Branch on
`error.code` and honour `retryable`; do not infer retryability from the status
class alone.

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
bounded to 50, and each chunk's `content` is capped (`truncated` flags when it
was cut) so a caller cannot pull unbounded filing text into a prompt.
`POST /v1/batch/filings/query` accepts 1–100 identities and returns a success
or typed error for each item.

## Question-directed retrieval

`GET /v1/filings/{stock_code}/{period}/context` accepts two relevance
parameters beyond `evidence_limit`:

| Parameter | Meaning |
| --- | --- |
| `question` | Free text (≤500 chars). Ranks chunks by cosine similarity against stored embeddings; each returned chunk carries `retrieval_score`. |
| `sections` | Repeatable section type, e.g. `sections=risk&sections=accounting_policy`. An unknown value returns 422 rather than silently matching nothing. |

```
GET /v1/filings/2330/2025Q1/context?question=會計政策有什麼變更&sections=accounting_policy&evidence_limit=5
```

Both are optional and degrade rather than fail — and the response says so.
Every context envelope carries a required `retrieval` object describing how
`evidence_chunks` were actually selected:

```json
{"mode": "semantic",   "state": "present",          "detail": null}
{"mode": "importance", "state": "not_applicable",   "detail": "no question was supplied; ..."}
{"mode": "importance", "state": "provider_failure", "detail": "the embedding model is unavailable, ..."}
{"mode": "importance", "state": "missing",          "detail": "this filing has no chunk embeddings, ..."}
```

`mode` is `semantic` only when the question actually ranked the results.
`state` reuses the `DataState` vocabulary the snapshot path already applies
per field, so an existing consumer parses it unchanged. `detail` is populated
whenever `state` is not `present`.

This exists because the degraded paths were previously indistinguishable from a
real search: the response still carried well-formed chunks with section titles,
page numbers and chunk ids, and the only tell was a null `retrieval_score` a
caller would have had to notice. Consumers should branch on
`retrieval.state`, not on `retrieval_score`.

Embeddings are generated offline with `fr embed` (requires
`uv sync --extra vector`). The command is resumable — chunks that already have
an embedding are skipped — so it is safe to interrupt and restart, including
to move it onto a GPU host mid-run.

Each chunk carries what a citation needs: `chunk_id`, `doc_id`, `checksum`,
`source_url`, `page_number`, `section_type` and `section_title`. The source
document's local filesystem path is never exposed.

### Citation stability

`chunk_id` is only stable within one extraction. Re-extracting a filing deletes
and re-inserts its chunks, and because identity values keep climbing while the
old range stays occupied, a cached id does not reliably stop resolving — it can
silently return different text, from a different filing. Nothing else in the
envelope moves when that happens.

Every context envelope therefore carries `corpus_version`: an opaque token for
that filing's current chunk corpus, currently the ISO-8601 timestamp of its
newest chunk, null when it has none.

```json
{"corpus_version": "2026-09-06T07:51:30.369512+00:00"}
```

Store it alongside any cached `chunk_id` and compare by equality before citing.
If it differs, the ids are stale and must be re-fetched. It is per-filing on
purpose, so a consumer caching citations for one filing is not invalidated by an
unrelated filing being re-extracted.

For topic matching prefer `section_title` over `section_type`. Taiwan filing
notes are numbered, and the parser segments on that numbering and stores the
heading verbatim — 885 distinct titles across the corpus (`應收帳款`,
`無形資產`, `所得稅`, `營業收入`, …) against the dozen coarse `section_type`
values. A question naming a topic can be matched lexically against the title of
the note that actually covers it.

## Release status

API v1 and the FinMind/bank taxonomy baseline are merged into `main`. The
committed OpenAPI document and `tests/test_api_contract.py` are the compatibility
boundary for Financial Agent and other typed consumers. Feature branches used
during the rollout have been removed.

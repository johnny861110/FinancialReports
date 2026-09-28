# Change record — 2026-09-06

Engineering record for the retrieval-quality and storage-consolidation work of
2026-09-06. Written because the commits are local only (the GitHub account was
suspended at the time), so this file is the durable account of what changed and
why.

**摘要：** 本次工作以「檢索品質」為唯一衡量標準。修好三個「回報成功但實際沒做事」
的缺陷、把附註切分改成依編號標題（回收 885 個主題標籤）、重建整個語料庫，並移除
所有非 Postgres/pgvector 的殘留。`risk` 標籤從 26.9% 降到 1.4%，四個探針查詢中
三個的命中率上升 7–12 個百分點。所有變更皆已在真實資料上驗證。

---

## 1. The theme: outputs that did not mean what they said

Four defects found on the same day turned out to be one habit — a degraded path
written to keep going quietly rather than to fail or disclose.

| Where | Reported | Actually happened |
|---|---|---|
| api container, `extract` | stage `completed`, filing `extracted` | `pdfplumber` absent → 0 pages, 0 chunks |
| `ingest` | stage `completed`, filing reaches `insight_ready` | all downloads returned `None`; no document obtained |
| `/context` retrieval | evidence chunks with sections and page numbers | embedding model absent → no semantic search ran |
| `quality_score` | a score, e.g. `0.8176`, with no stated maximum | two terms are structurally short, so 0.818 *is* full marks |

Each is individually defensible: import guards keep the API answering when
optional extras are missing, `if path:` avoids writing rows for documents that
were not downloaded, returning `None` keeps a request alive. Together they mean
no output could be assumed to mean what it said.

Three rules came out of it, and the first two are now implemented:

1. A stage may not report `completed` having produced nothing.
2. A composite score may not silently include a term that cannot be computed.
   *(Addressed by documentation rather than by changing the score — the ceiling
   is now stated where the score is defined and specified. See §6b.)*
3. A degraded path must mark its output as degraded where the caller sees it.

---

## 2. Retrieval quality

### 2.1 Section labelling rewritten

**Problem.** `document_sections.section_type` was noise. The five keyword
patterns (`notes`, `auditor`, `accounting_policy`, `eps_note`, `risk`) were bare
substrings with none of the guards the statement titles carry. `風險管理` matched
ordinary prose — "係依書面之風險管理政策", "風險管理部門依相關業務管理部門" — and
financial-holding filings discuss risk management on nearly every notes page. It
fired 418 times across 67 filings and claimed **26.9% of all chunks**.

The consequence was measurable: the chunks belonging to the accounts-receivable
note were labelled `risk` more often than anything else, and the income-tax note
took five different `section_type` values across filings. Section filtering had
been abandoned by the consumer for exactly this reason.

**A hypothesis that was tested and refuted.** It was initially thought that a
section stayed open until the next recognised heading, so an unclosed section ran
to the end of the document. Two measurements say otherwise: detection is
page-granular (`_detect_section` reads only the first 800 characters of each
page, so heading position within a page plays no part), and `risk` was 418
separate sections averaging 6.0 pages, of which only 10 reached the document end.
The defect was over-firing, not under-closing.

**Fix, in two parts.**

- The five keyword patterns must now match at a line start, optionally behind
  note numbering, and the line must read as a heading: 2–30 characters, at least
  two CJK characters, not ending in `。，；`, no cross-reference (`請參閱`/`詳見`),
  no table-of-contents page range, no ditto mark or comma-grouped figures.
- Taiwan filing notes are rigidly numbered (`十、應收帳款`,
  `（四）財務風險管理目的與政策`, `2.風險管理政策`). That numbering is the only
  regular boundary the document actually carries. A numbered heading now starts
  its own section, typed `note`, titled with the heading text.

**`section_type` resets to `note` rather than inheriting.** A note about
無形資產 sitting inside a stretch typed `risk` is not merely coarse, it is wrong,
and it misleads anything that trusts the field. The data supports this: 28.5% of
numbered headings (1,098 of 3,851) occur while the inherited type is a
*statement* type, and inspection shows they are genuine notes (`公司沿革`,
`編製基礎`, `部門資訊`, `其他收入`) inside statement sections that over-ran. In
every one of those cases resetting is the truthful action.

### 2.2 Measured effect

Whole corpus re-extracted and re-embedded (67 filings, 0 failures).

| | Before | After |
|---|---|---|
| Chunks | 19,767 | 22,869 |
| Sections | 2,848 | 5,063 |
| `note`-typed sections | 0 | 3,688 |
| Distinct note titles | 0 | **885** |
| `risk` share of chunks | **26.9%** | **1.4%** |
| Median pages per section | — | 1.0 |

Four probe questions, top-10 dense retrieval, measured over every filing that
has a note with that title:

| Question | Before | After | Δ | Avg rank |
|---|---|---|---|---|
| 應收帳款 | 58% | **66%** | +8pp | 4.0 → 3.9 |
| 無形資產 | 45% | **57%** | +12pp | 4.7 → 4.2 |
| 所得稅 | 98% | 98% | — | 1.6 → 1.8 |
| 營業收入 | 70% | **77%** | +7pp | 3.4 → 2.6 |

Dense ranking itself was not changed. The gain comes from the chunks: with
sections segmented per numbered note, a chunk is far more likely to be about
exactly one topic, so its embedding is a cleaner match. 所得稅 was already at
ceiling.

*Method caveat:* "before" identified the target note using labels simulated
offline over the old chunks; "after" uses the labels actually stored. Same notes,
not an identical procedure.

**A note on the metric.** Section-type concentration (median share of a filing's
chunks carrying its single largest `section_type`) was the original target and
was deliberately abandoned. It scores the spread over a dozen hard-coded types
and cannot see a per-note topic label — the numbered-heading change makes it
*worse* (56.0% → 62.0%) while plainly improving retrieval. It is also gameable:
firing fewer boundaries improves the number while making sections longer and
labels lazier. Prefer the probe measure above.

### 2.3 The HNSW index was removed

`idx_chunk_embeddings_hnsw` cost 80 MB and was never used. Evidence, measured
against the live database:

```
unfiltered ANN:              Index Scan using idx_chunk_embeddings_hnsw   ← usable
filtered to one filing,
with enable_seqscan = off:   Sort → Nested Loop → Bitmap Index Scan       ← index refused
```

Every retrieval query filters to a single `filing_key` (123 chunks for
`3661_2025Q1`, ~900 for the widest), so Postgres fetches that filing's vectors by
primary key and sorts them exactly in ~3 ms. An approximate scan over all 19,767
vectors followed by post-filtering to one filing is slower *and* lossier — HNSW
trades recall for speed and there is no speed to buy. Exact search is the higher
quality choice here, not merely an acceptable one.

The extension and the `VECTOR(768)` column are unchanged. The restore statement
is preserved in a comment in `schema.sql`.

> **A `DISTINCT ON (dc.content)` removal was implemented, measured, and then
> reverted.** It was 2.2× faster (7.0 ms → 3.1 ms) and provably identical on
> current data (zero duplicate contents within any filing). It was reverted
> because the benefit was ~4 ms on a request that runs in tens of milliseconds,
> and the cost was deleting a test that encodes "the evidence list never shows
> the same passage twice" — a product property that holds regardless of whether
> duplicates currently occur. The write path and the read path fail
> independently.

---

## 3. Availability: a blocking model load took the API down for nine hours

**Symptoms.** `unhealthy`, FailingStreak 95. The host could not reach port 8010
at all, nor the container IP directly. The container-internal healthcheck timed
out. The process was alive the whole time — 39 PIDs, 384 MB, 0.01% CPU. From the
outside it looked like a running service.

**Cause — three things composing.**

1. `BAAI/bge-base-zh-v1.5` (~400 MB) lived only in the container's writable
   layer, so every `docker compose up` discarded it. The container cache was
   104 KB; the host had a complete 781 MB copy.
2. The next question-bearing request triggered a cold download, which stalled.
3. `encode_question` was called **synchronously inside an async handler**, with
   no threadpool and no timeout — unlike the refresh path, which correctly
   awaits. The stalled download blocked the event loop, so one request took down
   every endpoint including the healthcheck.

Nothing in the logs said any of this: the "model not installed" path returned
`None` on its first line with no message, and the only existing warning covered
an exception *during* encoding, which is the rare case.

**Fix, both halves.**

- `docker-compose.yml` mounts the host HuggingFace cache (read-write —
  `huggingface_hub` writes lock files beside the blobs) and sets
  `HF_HUB_OFFLINE=1`, so a deployed service never fetches a model at request
  time. A missing model now fails immediately instead of hanging.
- `app.py` runs the embed in `run_in_threadpool` under a 20-second
  `asyncio.wait_for`. A slow model now costs one request its semantic ranking
  instead of costing the service its availability — and that degradation is
  reported on the `retrieval` field.

**Verified.** Cold load from the mounted cache 10.3 s → HTTP 200,
`{"mode":"semantic","state":"present"}`. Warm 0.071 s. Healthy, streak 0.

---

## 4. Contract change: `ContextEnvelope.retrieval`

Required object on every context envelope.

```json
{"mode": "semantic",   "state": "present",          "detail": null}
{"mode": "importance", "state": "not_applicable",   "detail": "no question was supplied; ..."}
{"mode": "importance", "state": "provider_failure", "detail": "the embedding model is unavailable, ..."}
{"mode": "importance", "state": "missing",          "detail": "this filing has no chunk embeddings, ..."}
```

`state` reuses the existing `DataState` enum, which the snapshot path already
applies per field, so an existing consumer parses it unchanged. The predicate is
shared with `get_chunks` (`APIRepository.uses_semantic_ranking`) so the reported
state cannot drift from the branch that actually ran.

Verified under genuine degradation, not only in tests: during the re-embed, a
filing not yet processed returned real chunks alongside
`{"mode":"importance","state":"missing","detail":"... Run \`fr embed\` for it"}`.

`docs/openapi-v1.json` was regenerated. Note it was regenerated **matching the
committed file's key order**, not `export_openapi.py`'s `sort_keys=True` — the
script and the committed artifact disagree, and using the script would have
reordered all 4,000 lines and buried a 43-line change. See §7.

---

## 5. Storage consolidation (Postgres + pgvector only)

The directive was already satisfied in code; what remained was dead weight.

- **Removed the `vector-store` (chromadb) extra.** Nothing imported it. Relocking
  took `uv.lock` from **164 to 85 packages**, dropping onnxruntime, kubernetes,
  grpcio, the opentelemetry set, posthog and 43 others.
- **Removed unused dependencies**, each verified absent from `src/`, `tests/` and
  `scripts/`, with no dynamic-import machinery anywhere in the codebase:
  `pandas`, `python-dateutil`, `pyyaml` (all three were *base* dependencies, so
  they shipped in every image), `tiktoken`, and the entire `ocr` extra
  (`paddleocr`, `paddlepaddle`, `opencv-python` — there is no `ocr` reference in
  `src/` at all). `pypdfium2` turned out to be a hard dependency of `pdfplumber`,
  so declaring it separately was redundant rather than wrong.
  Verified behaviourally: the full suite passes in an environment holding only
  the base and dev dependencies.
- **`all` is now self-referential** (`financial-reports[pdf,vector,llm]`) so it
  cannot drift out of step again.
- **Deleted `scripts/migrate_sqlite_to_postgres.py` and `scripts/verify_parity.py`.**
  The migration completed in `5cc2552`; these were the last `sqlite3` imports.
  `ci.yml`'s lint paths were updated — `ruff` exits 1 on a missing path, so CI
  would have broken otherwise.
- **Fixed 15 stale documentation lines** that described SQLite or chromadb as
  present tense, including three source docstrings and stale comments in
  `docker-compose.yml` and `ci.yml`. Historical references in `CHANGELOG.md`,
  `schema.sql` and `tests/conftest.py` were left alone — they are accurate as
  history.

---

## 6. Operational notes

### Run `fr embed` on the host when a GPU is available

The container pins CPU-only torch deliberately: no GPU passthrough is configured
in compose, this keeps ~5 GB out of the image, and the API itself never embeds.
That pin is correct and should stay. But `fr embed` is an offline batch job with
no reason to run in the container.

| | Container (CPU) | Host (RTX 3060) |
|---|---|---|
| Throughput | ~128 chunks/min | **~2,150 chunks/min** |
| 18,105 chunks | ~2.4 hours | **~9 minutes** |

About **17×**. `fr embed` is resumable by design, so switching mid-run costs
nothing.

### A corpus re-extract must run `extract → validate → insights`

Re-extracting with `force` resets each filing to `extracted`, which is below the
threshold `build_envelope` requires. Running `extract` alone leaves every filing
returning **HTTP 409 `filing_not_ready`** on `/context` and `/snapshot`. This
happened during this work and caused a brief consumer-facing outage; it was
caught in verification and repaired by running validate and insights (15
seconds for 67 filings).

### Re-extract cost

67 filings, 28 minutes for parsing, plus embedding (9 minutes on GPU). An
earlier estimate of "15–25 minutes dominated by PDF parsing" was wrong in both
magnitude and attribution — embedding was the dominant cost until it was moved
to the GPU.

---

## 6b. FinMind is the structured source — settled, not a gap

Recorded prominently because everything measured on 2026-09-06 points at this
like a defect, and the next person to look will otherwise try to "fix" it.

**Every fact in the corpus has `source_type` = `finmind`. Zero XBRL, zero
iXBRL. No filing holds an XBRL or iXBRL source document at all — all 67
documents are PDFs.** The XBRL and iXBRL parsers have never produced a fact.

This is a deliberate architectural choice, confirmed with the project owner.
The project uses the FinMind API for structured data on purpose; PDFs supply
the text that retrieval runs over. It is **not** an ingestion failure and not
a parser defect.

It looks like one from the inside, which is why it is written down here and in
three other places (`src/sources/finmind_client.py`, `src/pipeline/extract.py`,
`SPEC.md` §2.4):

- `financial_facts` has an `xbrl_tag` column, populated with FinMind's key names
- `taxonomy.py` lists `xbrl_tags` for every canonical field
- `extract.py` has an XBRL branch that never fires, and its comment calls
  FinMind a "fallback"
- `schema.sql`, the SPEC source table, and the pipeline docs all name XBRL first
- the quality score docks marks for source coverage FinMind cannot supply

Note the shape of the original diagnosis, because it changed the cost estimate
by an order of magnitude: the first reading was "the XBRL parser has never
worked", which is a parser project. The measurement showed no XBRL *document*
was ever obtained, which would have been a download question — and the answer
turned out to be that neither is broken, because neither was ever meant to run.

### The quality-score ceiling follows from it

`quality_score` cannot reach 1.0, and that is by design rather than a
deficiency to chase:

| Term | Current state | Cost |
|---|---|---|
| source coverage (40%) | FinMind is the only structured source and supplies 27 of 34 canonical fields on a typical filing | 0.40 × 7/34 ≈ 0.082 |
| evidence coverage (10%) | nothing writes `fact_evidence`, so it is 0 for every filing | 0.100 |

An otherwise-perfect filing therefore scores **≈ 0.818**, and the observed
corpus maximum is exactly 0.8176. Verified by decomposition: filings grouped by
covered-field count each hit their own theoretical maximum precisely — 27
covered → 0.8176, 21 covered → 0.7471.

Read the score as a *relative* measure between filings, not as a percentage of
an attainable ideal. This is documented where the score is defined
(`src/validation/quality_score.py`) and where it is specified (SPEC §12). If it
should instead state its own maximum in the response, the natural shape is a
`quality_score_max` field alongside it — deliberately not added, because it is
a contract change and the ceiling is presently a documentation problem.

---

## 7. Known-open items

Deliberately not addressed. Listed so they are not lost.

Ordered by how quietly they fail, most first.

| Item | Detail |
|---|---|
| **`quality_score` states no maximum over the wire** | **Top of the next list.** §6b documents the ~0.818 ceiling for anyone reading the code, but a consumer still receives `0.8176` with no maximum attached and reasonably reads it as 82% of achievable. That is the same silent-wrongness this pass removed from values, surviving in a metric. Documentation closes it for the reader and not for the caller. The fix is a `quality_score_max` field alongside the score; it is small, and it was held back only because adding a contract change at wrap-up turns a clean stopping point into a half-finished one. |
| `fact_evidence` never written | Read by `/evidence` and by `quality_score`; 0 rows. Costs a flat 0.10 of every score (see §6b for the full ceiling). Deferred on its own merits: writing evidence recovers at most 0.10 and is real work. Decide it when someone wants `/evidence` to function. |
| `text_summaries`, `insight_evidence` | Defined in schema and SPEC, referenced by no code, 0 rows. |
| `source_documents.checksum` | Read by the API and exposed in the contract, never written — 67/67 NULL. Removing it is a contract change. |
| `document_pages` | 7,875 rows, 16 MB, INSERT/DELETE only with no `SELECT` anywhere. Page-level granularity exists and nothing retrieves at it — an unused retrieval asset rather than dead weight. |
| Schema DDL on every `FilingStore()` | `__init__` runs the whole of `schema.sql` on every construction. Requires `CREATE EXTENSION` rights, and `IF NOT EXISTS` never alters an existing table, so the next column change will silently not apply to a populated database. Needs Alembic. |
| Job registry in memory | `src/api/jobs.py` holds refresh jobs in a process-local dict, never evicted. With `restart: unless-stopped`, every in-flight `job_id` 404s after a restart. The last application state outside Postgres. |
| Two chunk-read paths | `FilingStore.get_chunks` (unbounded, no ranking) serves the agent/CLI; `APIRepository.get_chunks` serves HTTP. They can answer the same question differently. `ChunkRetriever.search_keyword` is an unindexed `LIKE` scan. |
| `export_openapi.py` disagrees with the artifact | The script writes `sort_keys=True`; the committed `docs/openapi-v1.json` is in insertion order. Anyone regenerating with the script gets a 4,000-line reordering. |
| `data/financial.db` and friends | 329 MiB orphaned SQLite file, plus `data/downloads/` and `data/master_index.json`. Read by nothing. Untracked user data — deletion needs the owner's say-so. |

---

## 8. Verification performed

- `ruff check`, `ruff format --check`, `mypy` — clean.
- **144 tests passing** against a real PostgreSQL, up from 122. New coverage:
  four retrieval states, seven section-labelling cases, three ingest-failure
  cases (`tests/test_pipeline.py` is the first test file for the ingest stage),
  the no-source-documents invariant and its demotion path, `corpus_version`
  moving when the corpus changes, the FinMind unit conversion including the
  sub-NT$1,000 case the old guard mis-scaled, and the 409 contract.
- Dependency removal proven behaviourally in an environment holding only base
  and dev dependencies.
- The `pdf`-extra fix proven end to end inside the container against a
  throwaway database: 51 pages, 50 sections, 149 chunks from a cached PDF, where
  the same run previously produced nothing.
- Live corpus: 70 filings all `insight_ready`, 22,869 chunks, 22,869 embeddings,
  database 188 MB.
- Container: healthy, running as `appuser`, `/health/ready` ready,
  `/v1/stocks` returns 15 companies.
- All three document-less filings return `409 filing_has_no_source_documents`
  with `retryable: false` on **both** `/snapshot` and `/context`.
- Cross-checked end to end from the consuming project through the real stack —
  browser, live LLM, this container. Two results worth recording: a query
  against an empty filing now degrades to a stated data gap rather than an
  error, and 「資本管理政策為何？」 against 3661/2025Q1 — a question that was
  being silently discarded that morning — returns an answer grounded on
  現金流量資訊, 合併基礎 and 財務風險管理目的與政策.
- That end-to-end pass also caught a defect no unit test would have: the 409
  was handled on one consumer path and not the other, so an internal host,
  port and percent-encoded query string were being rendered into a user-facing
  data-gap list. Fixed consumer-side. Worth remembering that the last two
  defects of the day were both found by running the whole thing, not by
  testing the parts.

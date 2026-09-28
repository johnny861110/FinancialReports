#!/usr/bin/env bash
#
# Container smoke test — checks the things no in-process test can see.
#
# The producer's worst defect of 2026-09-06 was an image missing the `pdf`
# extra. Extraction then produced zero pages and zero chunks, reported the
# stage `completed`, and marked the filing `extracted` so a later run skipped
# it. The unit suite was green throughout and could not have been otherwise:
# pdfplumber is installed in the dev environment, so nothing pytest can run
# says anything about what is in the image.
#
# So this asserts against the *running container* and the *live API*:
#   - the environment the process actually has, read with printenv rather than
#     from compose (compose substitutes from .env, so the file and the process
#     can disagree -- that discrepancy is itself a defect this catches)
#   - that imports resolve inside the image, including that removed
#     dependencies are really gone
#   - that the API surfaces behave, with expected values derived from the API
#     rather than hardcoded, so a re-ingest does not turn this red
#
# Usage:   scripts/container_smoke.sh
# Exit:    0 all checks passed, 1 otherwise.
#
# Watch it fail before trusting it: `docker compose stop api` should turn most
# of this red. A smoke test nobody has seen fail is just another false green.

set -uo pipefail

API_CONTAINER="${API_CONTAINER:-financialreports-api-1}"
DB_CONTAINER="${DB_CONTAINER:-financialreports-db-1}"
API="${API_BASE_URL:-http://localhost:8010}"

pass=0
fail=0

ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; fail=$((fail + 1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

check() {  # check <description> <expected> <actual>
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi
}

contains() {  # contains <description> <needle> <haystack>
  case "$3" in *"$2"*) ok "$1" ;; *) bad "$1 (missing '$2' in: ${3:0:120})" ;; esac
}

head_ "Containers"
for c in "$API_CONTAINER" "$DB_CONTAINER"; do
  status=$(docker inspect -f '{{.State.Health.Status}}' "$c" 2>/dev/null || echo absent)
  check "$c healthy" "healthy" "$status"
  policy=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$c" 2>/dev/null || echo absent)
  check "$c restarts unless stopped" "unless-stopped" "$policy"
done
check "api runs as non-root" "appuser" \
  "$(docker exec "$API_CONTAINER" whoami 2>/dev/null || echo absent)"

head_ "Environment as the process actually has it"
# printenv, not the compose file: compose substitutes from .env, so the two can
# disagree and only the process's own view is the truth.
env_of() { docker exec "$API_CONTAINER" printenv "$1" 2>/dev/null || echo unset; }
check "HF_HUB_OFFLINE=1 (never fetch a model at request time)" "1" "$(env_of HF_HUB_OFFLINE)"
check "FR_OUTPUT_DIR" "/app/data/raw" "$(env_of FR_OUTPUT_DIR)"
contains "FR_DATABASE_URL points at the compose db" "@db:5432" "$(env_of FR_DATABASE_URL)"

head_ "Imports resolve in the image"
# The check that would have caught the pdf extra. Nothing in pytest can.
for mod in pdfplumber sentence_transformers; do
  got=$(docker exec "$API_CONTAINER" python3 -c "import $mod; print('yes')" 2>/dev/null || echo no)
  check "$mod importable" "yes" "$got"
done
# Removed dependencies must really be gone, or the image is not what the
# manifest says it is.
for mod in chromadb pandas; do
  got=$(docker exec "$API_CONTAINER" python3 -c "import $mod" 2>/dev/null && echo present || echo absent)
  check "$mod absent" "absent" "$got"
done
model=$(docker exec "$API_CONTAINER" sh -c \
  'test -d ~/.cache/huggingface/hub/models--BAAI--bge-base-zh-v1.5 && echo mounted || echo missing' 2>/dev/null)
check "embedding model cache mounted" "mounted" "$model"

head_ "Schema"
idx=$(docker exec "$DB_CONTAINER" psql -U financial -d financial -tAc \
  "SELECT count(*) FROM pg_indexes WHERE indexname='idx_chunk_embeddings_hnsw'" 2>/dev/null)
# Startup runs the whole of schema.sql, so this also proves it does not
# recreate an index that was deliberately dropped.
check "no ANN index recreated at startup" "0" "${idx:-error}"

head_ "API"
# curl already prints 000 when it cannot connect, so no `|| echo` fallback --
# that appended a second 000 and reported '000000'.
code() { curl -sS -o /dev/null -w '%{http_code}' --max-time 90 "$1" 2>/dev/null; }
body() { curl -sS --max-time 90 "$1" 2>/dev/null; }

check "/health/ready" "200" "$(code "$API/health/ready")"

stocks=$(body "$API/v1/stocks?limit=100")
n=$(printf '%s' "$stocks" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["items"]))' 2>/dev/null)
if [ "${n:-0}" -gt 0 ] 2>/dev/null; then ok "/v1/stocks returns $n companies"; else bad "/v1/stocks returned nothing"; fi

# Values are derived from the API, never hardcoded, so a re-ingest cannot turn
# this red for the wrong reason.
target=$(python3 - <<'PY' 2>/dev/null
import json, urllib.request
base = "http://localhost:8010"
stocks = json.load(urllib.request.urlopen(f"{base}/v1/stocks?limit=100", timeout=60))["items"]
for s in stocks:
    code = s["stock_code"]
    periods = json.load(urllib.request.urlopen(
        f"{base}/v1/stocks/{code}/periods", timeout=60)).get("items", [])
    for p in periods:
        period = p["period"] if isinstance(p, dict) else p
        try:
            urllib.request.urlopen(f"{base}/v1/filings/{code}/{period}/snapshot", timeout=60)
        except Exception:
            continue
        print(f"{code} {period}")
        raise SystemExit
PY
)
if [ -z "$target" ]; then
  bad "no servable filing found to exercise /context"
else
  set -- $target
  stock=$1; period=$2
  ok "servable filing discovered: $stock/$period"
  ctx=$(body "$API/v1/filings/$stock/$period/context?question=%E6%87%89%E6%94%B6%E5%B8%B3%E6%AC%BE&evidence_limit=3")
  fields=$(printf '%s' "$ctx" | python3 -c '
import json, sys
d = json.load(sys.stdin)
r = d.get("retrieval") or {}
print(r.get("mode"), r.get("state"),
      "corpus" if d.get("corpus_version") else "nocorpus",
      len(d.get("evidence_chunks") or []))' 2>/dev/null)
  set -- ${fields:-none none none 0}
  check "retrieval.mode is semantic (model reachable in the image)" "semantic" "$1"
  check "retrieval.state is present" "present" "$2"
  check "corpus_version published" "corpus" "$3"
  if [ "${4:-0}" -gt 0 ] 2>/dev/null; then ok "evidence chunks returned ($4)"; else bad "no evidence chunks"; fi
fi

# A filing with no source document must be a non-retryable conflict, not a 503:
# a consumer retrying a 5xx reports the whole producer as down over one empty
# filing, and a real outage stops being distinguishable from it.
empty=$(docker exec "$DB_CONTAINER" psql -U financial -d financial -tAc \
  "SELECT f.filing_key FROM filings f LEFT JOIN source_documents sd ON sd.filing_id=f.id
   GROUP BY 1 HAVING count(sd.id)=0 LIMIT 1" 2>/dev/null | tr -d ' \r')
if [ -z "$empty" ]; then
  ok "no document-less filings to check"
else
  s=${empty%%_*}; p=${empty#*_}
  for ep in snapshot context; do
    check "$empty $ep -> 409" "409" "$(code "$API/v1/filings/$s/$p/$ep")"
  done
  err=$(body "$API/v1/filings/$s/$p/snapshot" | python3 -c '
import json,sys; e=json.load(sys.stdin)["error"]; print(e["code"], e["retryable"])' 2>/dev/null)
  check "  code and retryability" "filing_has_no_source_documents False" "${err:-none}"
fi

head_ "Result"
printf '  %d passed, %d failed\n\n' "$pass" "$fail"
[ "$fail" -eq 0 ]

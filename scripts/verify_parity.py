#!/usr/bin/env python3
"""Prove the Postgres migration changed no API behaviour.

A data migration is only trustworthy if the responses are provably identical,
so this dumps the same set of API responses from a build and diffs two dumps.
It talks to the app in-process via TestClient, reading whatever database the
environment configures, which lets the same command run against the old
SQLite-backed code (in a git worktree at the pre-migration commit) and the new
Postgres-backed code.

    # old code, old database
    git worktree add /tmp/pre-migration <pre-migration-sha>
    cp scripts/verify_parity.py /tmp/pre-migration/scripts/
    cd /tmp/pre-migration && FR_DB_PATH=<repo>/data/financial.db \
        uv run python scripts/verify_parity.py dump --out /tmp/before.json

    # new code, migrated database
    FR_DATABASE_URL=... uv run python scripts/verify_parity.py dump --out /tmp/after.json

    uv run python scripts/verify_parity.py diff /tmp/before.json /tmp/after.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUESTS: list[tuple[str, dict[str, Any]]] = [
    ("/v1/capabilities", {}),
    ("/v1/stocks", {}),
    ("/v1/stocks", {"limit": 5, "offset": 0}),
    ("/v1/stocks", {"limit": 200}),  # over the bound: 422 shape must match too
    ("/v1/filings/9999/2099Q4/snapshot", {}),  # absent filing: 404 shape
]

# Per-filing endpoints, expanded for each filing discovered at dump time.
FILING_PATHS = [
    ("/v1/filings/{stock}/{period}/snapshot", {}),
    ("/v1/filings/{stock}/{period}/context", {}),
    ("/v1/filings/{stock}/{period}/context", {"evidence_limit": 0}),
    ("/v1/filings/{stock}/{period}/context", {"evidence_limit": 50}),
]

# Values that legitimately differ between runs and would mask real diffs.
VOLATILE_KEYS = {"job_id", "generated_at", "requested_at"}


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_volatile(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [_strip_volatile(v) for v in value]
    return value


def dump(out_path: Path, max_filings: int) -> int:
    from fastapi.testclient import TestClient

    from src.api.app import create_app

    app = create_app()
    captured: dict[str, Any] = {}

    with TestClient(app) as client:
        for path, params in REQUESTS:
            response = client.get(path, params=params)
            key = f"GET {path} {json.dumps(params, sort_keys=True)}"
            captured[key] = {
                "status": response.status_code,
                "body": _strip_volatile(response.json()),
            }

        stocks = client.get("/v1/stocks", params={"limit": 100}).json()
        pairs: list[tuple[str, str]] = []
        for stock in stocks.get("items", [])[:max_filings]:
            code = stock["stock_code"]
            periods = client.get(f"/v1/stocks/{code}/periods").json()
            key = f"GET /v1/stocks/{code}/periods"
            captured[key] = {"status": 200, "body": _strip_volatile(periods)}
            for item in periods.get("items", [])[:2]:
                pairs.append((code, item["period"]))

        for code, period in pairs:
            for template, params in FILING_PATHS:
                path = template.format(stock=code, period=period)
                response = client.get(path, params=params)
                key = f"GET {path} {json.dumps(params, sort_keys=True)}"
                captured[key] = {
                    "status": response.status_code,
                    "body": _strip_volatile(response.json()),
                }

    out_path.write_text(json.dumps(captured, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"captured {len(captured)} responses -> {out_path}")
    return 0


def diff(before_path: Path, after_path: Path) -> int:
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))

    only_before = sorted(set(before) - set(after))
    only_after = sorted(set(after) - set(before))
    differing = [key for key in sorted(set(before) & set(after)) if before[key] != after[key]]

    for key in only_before:
        print(f"MISSING in after : {key}")
    for key in only_after:
        print(f"EXTRA   in after : {key}")
    for key in differing:
        print(f"DIFFERS          : {key}")
        b, a = before[key], after[key]
        if b.get("status") != a.get("status"):
            print(f"    status {b.get('status')} -> {a.get('status')}")
        else:
            _print_body_diff(b.get("body"), a.get("body"), path="body")

    total = len(set(before) | set(after))
    bad = len(only_before) + len(only_after) + len(differing)
    if bad:
        print(f"\n{bad} of {total} responses differ.")
        return 1
    print(f"\nAll {total} responses identical.")
    return 0


def _print_body_diff(before: Any, after: Any, path: str, depth: int = 0) -> None:
    if depth > 4:
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                _print_body_diff(before.get(key), after.get(key), f"{path}.{key}", depth + 1)
        return
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            print(f"    {path}: length {len(before)} -> {len(after)}")
            return
        for index, (b, a) in enumerate(zip(before, after)):
            if b != a:
                _print_body_diff(b, a, f"{path}[{index}]", depth + 1)
        return
    print(f"    {path}: {before!r} -> {after!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    dump_parser = sub.add_parser("dump", help="Capture API responses to a file")
    dump_parser.add_argument("--out", required=True, type=Path)
    dump_parser.add_argument("--max-filings", type=int, default=8)

    diff_parser = sub.add_parser("diff", help="Compare two captures")
    diff_parser.add_argument("before", type=Path)
    diff_parser.add_argument("after", type=Path)

    args = parser.parse_args()
    if args.command == "dump":
        return dump(args.out, args.max_filings)
    return diff(args.before, args.after)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Copy an existing SQLite database into PostgreSQL.

One-way migration for the SQLite -> Postgres move. Primary keys are preserved
verbatim: document_chunks.id is the stable chunk id the context endpoint
exposes and citations will reference, so renumbering rows would silently
invalidate every reference to them. Identity sequences are reset afterwards so
subsequent inserts do not collide with the copied ids.

Usage:
    python scripts/migrate_sqlite_to_postgres.py \
        --sqlite data/financial.db \
        --url postgresql+psycopg://financial:financial@localhost:5432/financial
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# Parent-before-child: every table is inserted after the tables it references.
TABLES: list[str] = [
    "companies",
    "filings",
    "source_documents",
    "financial_facts",
    "fact_evidence",
    "document_pages",
    "document_sections",
    "document_chunks",
    "chunk_embeddings",
    "text_summaries",
    "financial_metrics",
    "period_comparisons",
    "detected_events",
    "insight_cards",
    "insight_evidence",
    "validation_results",
    "pipeline_runs",
]

# Columns stored as 0/1 in SQLite that are BOOLEAN in Postgres.
BOOLEAN_COLUMNS: dict[str, set[str]] = {
    "document_pages": {"has_tables"},
    "document_chunks": {"contains_numbers", "contains_table"},
    "validation_results": {"passed"},
}

# Tables whose primary key is an identity column needing its sequence reset.
IDENTITY_TABLES = [t for t in TABLES if t != "chunk_embeddings"]

BATCH_SIZE = 2000


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _coerce(table: str, columns: list[str], row: sqlite3.Row) -> dict:
    booleans = BOOLEAN_COLUMNS.get(table, set())
    values = {}
    for column in columns:
        value = row[column]
        if column in booleans and value is not None:
            value = bool(value)
        values[column] = value
    return values


def migrate_table(sqlite_conn: sqlite3.Connection, pg_engine, table: str) -> int:
    columns = _sqlite_columns(sqlite_conn, table)
    if not columns:
        print(f"  {table:22s} skipped (absent from source)")
        return 0

    total = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    if total == 0:
        print(f"  {table:22s} 0")
        return 0

    column_list = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    # OVERRIDING SYSTEM VALUE is required to write explicit ids into a
    # GENERATED ALWAYS AS IDENTITY column.
    statement = text(
        f"INSERT INTO {table} ({column_list}) OVERRIDING SYSTEM VALUE VALUES ({placeholders})"
    )

    copied = 0
    cursor = sqlite_conn.execute(f"SELECT {column_list} FROM {table}")
    while True:
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break
        payload = [_coerce(table, columns, row) for row in rows]
        with pg_engine.begin() as conn:
            conn.execute(statement, payload)
        copied += len(rows)
        if total > BATCH_SIZE:
            print(f"  {table:22s} {copied}/{total}", end="\r", flush=True)

    print(f"  {table:22s} {copied}{' ' * 20}")
    return copied


def reset_sequences(pg_engine) -> None:
    """Point each identity sequence past the highest copied id."""
    with pg_engine.begin() as conn:
        for table in IDENTITY_TABLES:
            conn.execute(
                text(
                    "SELECT setval("
                    "  pg_get_serial_sequence(:table, 'id'),"
                    "  COALESCE((SELECT MAX(id) FROM " + table + "), 1),"
                    "  (SELECT MAX(id) IS NOT NULL FROM " + table + ")"
                    ")"
                ),
                {"table": table},
            )


def verify(sqlite_conn: sqlite3.Connection, pg_engine) -> bool:
    """Compare row counts and max ids; any mismatch means the copy is wrong."""
    ok = True
    print("\nVerification (source -> target):")
    with pg_engine.connect() as conn:
        for table in TABLES:
            if not _sqlite_columns(sqlite_conn, table):
                continue
            src = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            dst = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            same_count = src == dst

            detail = ""
            if table in IDENTITY_TABLES and src:
                src_max = sqlite_conn.execute(f"SELECT MAX(id) FROM {table}").fetchone()[0]
                dst_max = conn.execute(text(f"SELECT MAX(id) FROM {table}")).scalar_one()
                if src_max != dst_max:
                    same_count = False
                    detail = f"  max(id) {src_max} != {dst_max}"

            status = "ok" if same_count else "MISMATCH"
            ok = ok and same_count
            print(f"  {table:22s} {src:>8,} -> {dst:>8,}  {status}{detail}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, type=Path, help="Source SQLite file")
    parser.add_argument("--url", required=True, help="Target PostgreSQL URL")
    parser.add_argument(
        "--allow-non-empty",
        action="store_true",
        help="Proceed even if the target already holds rows (may violate unique keys)",
    )
    args = parser.parse_args()

    if not args.sqlite.exists():
        print(f"error: {args.sqlite} does not exist", file=sys.stderr)
        return 1

    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row
    pg_engine = create_engine(args.url, pool_pre_ping=True)

    # The target schema must already exist; FilingStore creates it on init.
    from src.storage.store import FilingStore

    FilingStore(args.url)

    with pg_engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM filings")).scalar_one()
    if existing and not args.allow_non_empty:
        print(
            f"error: target already contains {existing} filings. "
            "Re-run against an empty database, or pass --allow-non-empty.",
            file=sys.stderr,
        )
        return 1

    print(f"Migrating {args.sqlite} -> {args.url}\n")
    for table in TABLES:
        migrate_table(sqlite_conn, pg_engine, table)

    reset_sequences(pg_engine)
    ok = verify(sqlite_conn, pg_engine)

    sqlite_conn.close()
    pg_engine.dispose()

    print("\nMigration complete." if ok else "\nMigration FAILED verification.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

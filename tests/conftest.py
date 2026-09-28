"""Shared test fixtures.

The suite runs against a real PostgreSQL instance (the docker-compose `db`
service, or the pgvector service container in CI). Isolation that a temporary
SQLite file used to provide now comes from a throwaway database per session
plus a schema per test.

The throwaway database matters, and a schema inside the developer's working
database is not enough: `search_path` would have to include the schema holding
the `vector` extension, and if that is `public` then `CREATE TABLE IF NOT
EXISTS` resolves through the search path, finds the real tables, and silently
skips creating the test ones -- leaving the whole suite running against live
data. A fresh database has an empty `public`, so nothing can be shadowed.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from urllib.parse import quote

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.storage.store import resolve_database_url


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """Create a throwaway database for the session and drop it afterwards."""
    admin_url = resolve_database_url(os.getenv("FR_TEST_DATABASE_URL"))
    # Short connect timeout: when the database is absent this fixture is the
    # only thing standing between a misconfigured run and a false green, so it
    # should reach that verdict in seconds rather than minutes.
    engine = create_engine(
        admin_url,
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 3},
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        engine.dispose()
        message = (
            f"PostgreSQL is not reachable at {admin_url!r} ({exc}).\n"
            "\n"
            "56 of this suite's tests need it -- every storage, API-contract and\n"
            "pipeline-chain test -- so without it the run covers 94 of 150 and\n"
            "still exits 0. Refusing rather than skipping, because a green result\n"
            "over work that did not happen is worse than a red one.\n"
            "\n"
            "  start it:      docker compose up -d db\n"
            "  point at it:   export FR_DATABASE_URL=postgresql+psycopg://"
            "financial:financial@localhost:${POSTGRES_PORT:-5432}/financial\n"
            "\n"
            "The port matters: compose publishes POSTGRES_PORT from .env, which is\n"
            "not always 5432. If the URL above names a port you did not choose,\n"
            "that is the bug.\n"
            "\n"
            "To run only the tests that need no database, set FR_ALLOW_DB_SKIP=1 --\n"
            "deliberately, and read the skip count."
        )
        if os.getenv("FR_ALLOW_DB_SKIP"):
            pytest.skip(message)
        raise RuntimeError(message) from exc

    name = f"fr_test_{uuid.uuid4().hex[:12]}"
    with engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))

    test_url = make_url(admin_url).set(database=name)
    test_engine = create_engine(test_url, isolation_level="AUTOCOMMIT")
    with test_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    test_engine.dispose()

    try:
        yield test_url.render_as_string(hide_password=False)
    finally:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
                    " WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        engine.dispose()


@pytest.fixture
def database_url(postgres_url: str) -> Iterator[str]:
    """Yield a URL bound to a disposable schema unique to this test."""
    schema = f"t_{uuid.uuid4().hex[:12]}"
    engine = create_engine(postgres_url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    separator = "&" if "?" in postgres_url else "?"
    # public carries only the vector extension in this database, so putting it
    # last resolves the type without exposing any tables.
    options = quote(f"-csearch_path={schema},public")
    try:
        yield f"{postgres_url}{separator}options={options}"
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()

"""Shared test fixtures.

The suite runs against a real PostgreSQL instance (docker-compose service `db`,
or the `pgvector/pgvector` service container in CI). Isolation that a temporary
SQLite file used to provide is now provided by giving each test its own schema:
the connection sets `search_path` to that schema, so every unqualified table
name in the store resolves inside it, and the schema is dropped afterwards.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from urllib.parse import quote

import pytest
from sqlalchemy import create_engine, text

from src.storage.store import resolve_database_url


def _admin_url() -> str:
    return resolve_database_url(os.getenv("FR_TEST_DATABASE_URL"))


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """Base connection URL.

    Skipping is a local-developer convenience only. In CI an unreachable
    database must fail loudly: silently skipping every database test would let
    the pipeline report green while covering nothing.
    """
    url = _admin_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        message = (
            f"PostgreSQL is not reachable at {url!r} ({exc}). "
            "Start it with `docker compose up -d db`."
        )
        if os.getenv("CI"):
            raise RuntimeError(message) from exc
        pytest.skip(message)
    finally:
        engine.dispose()
    return url


@pytest.fixture
def database_url(postgres_url: str) -> Iterator[str]:
    """Yield a URL bound to a disposable schema unique to this test."""
    schema = f"test_{uuid.uuid4().hex[:12]}"
    engine = create_engine(postgres_url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    separator = "&" if "?" in postgres_url else "?"
    scoped_url = f"{postgres_url}{separator}options={quote(f'-csearch_path={schema}')}"
    try:
        yield scoped_url
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()

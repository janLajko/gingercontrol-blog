from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from src.config import settings
from src.db.connection import normalize_psycopg_conninfo


DB_POOL_NAME = "agent-system-invitation-code"
DB_POOL_APPLICATION_NAME = "agent-system-invitation-code"

DB_POOL_MIN_SIZE = int(os.getenv("INVITATION_CODE_DB_POOL_MIN_SIZE", "1"))
DB_POOL_MAX_SIZE = int(os.getenv("INVITATION_CODE_DB_POOL_MAX_SIZE", "10"))
DB_POOL_ACQUIRE_TIMEOUT_SECONDS = int(
    os.getenv("INVITATION_CODE_DB_POOL_ACQUIRE_TIMEOUT_SECONDS", "60")
)
DB_POOL_CONNECT_TIMEOUT_SECONDS = int(
    os.getenv("INVITATION_CODE_DB_POOL_CONNECT_TIMEOUT_SECONDS", "10")
)
DB_POOL_MAX_WAITING = int(os.getenv("INVITATION_CODE_DB_POOL_MAX_WAITING", "10"))

_pool: ConnectionPool[Connection[dict[str, Any]]] | None = None


def open_pool() -> None:
    global _pool

    if _pool is not None:
        return

    pool = _create_pool()

    try:
        pool.open(wait=True)
    except Exception:
        pool.close()
        raise

    _pool = pool


def close_pool() -> None:
    global _pool

    if _pool is not None:
        _pool.close()

    _pool = None


@contextmanager
def acquire_connection() -> Iterator[Connection[dict[str, Any]]]:
    with _require_open().connection() as conn:
        yield conn


@contextmanager
def acquire_connection_with_transaction() -> Iterator[Connection[dict[str, Any]]]:
    with _require_open().connection() as conn:
        with conn.transaction():
            yield conn


def _create_pool() -> ConnectionPool[Connection[dict[str, Any]]]:
    return ConnectionPool(
        conninfo=_database_url(),
        kwargs={
            "application_name": DB_POOL_APPLICATION_NAME,
            "connect_timeout": DB_POOL_CONNECT_TIMEOUT_SECONDS,
            "row_factory": dict_row,
        },
        min_size=DB_POOL_MIN_SIZE,
        max_size=DB_POOL_MAX_SIZE,
        name=DB_POOL_NAME,
        timeout=DB_POOL_ACQUIRE_TIMEOUT_SECONDS,
        max_waiting=DB_POOL_MAX_WAITING,
        check=ConnectionPool.check_connection,
        open=False,
    )


def _require_open() -> ConnectionPool[Connection[dict[str, Any]]]:
    if _pool is None:
        raise RuntimeError("invitation code database pool is not open")
    return _pool


def _database_url() -> str:
    if not settings.BILLING_DATABASE_URL:
        raise RuntimeError(
            "Set BILLING_DATABASE_URL before opening invitation code database pool"
        )

    return normalize_psycopg_conninfo(settings.BILLING_DATABASE_URL)

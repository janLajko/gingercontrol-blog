"""Database engine and session helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings

Base = declarative_base()

_engine: Optional[Engine] = None
_session_local = None
_billing_engine: Optional[Engine] = None
_billing_session_local = None


def get_engine() -> Optional[Engine]:
    """Return a singleton SQLAlchemy engine when DATABASE_URL is configured."""
    global _engine
    if _engine is None and settings.DATABASE_URL:
        _engine = create_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)
    return _engine


def get_session_local():
    """Return a configured session factory."""
    global _session_local
    engine = get_engine()
    if engine is None:
        return None
    if _session_local is None:
        _session_local = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_local


def get_billing_engine() -> Optional[Engine]:
    """Return a singleton SQLAlchemy engine for billing persistence."""

    global _billing_engine
    billing_database_url = settings.BILLING_DATABASE_URL or settings.DATABASE_URL
    if _billing_engine is None and billing_database_url:
        _billing_engine = create_engine(
            billing_database_url,
            future=True,
            pool_pre_ping=True,
        )
    return _billing_engine


def get_billing_session_local():
    """Return a configured session factory for billing persistence."""

    global _billing_session_local
    engine = get_billing_engine()
    if engine is None:
        return None
    if _billing_session_local is None:
        _billing_session_local = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _billing_session_local

"""SQLAlchemy engine, session factory, and request-scoped database dependency."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.config import get_database_url


class Base(DeclarativeBase):
    """Declarative base shared by all persisted AutoBook entities."""


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Build and cache the SQLAlchemy engine.

    Returns:
        An engine configured for the current ``DATABASE_URL``.
    """
    return create_engine(get_database_url(), pool_pre_ping=True)


def get_session_factory() -> sessionmaker[Session]:
    """Return a session factory bound to the cached application engine.

    Returns:
        A SQLAlchemy session factory with expiration disabled after commit.
    """
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session and close it afterwards.

    Yields:
        A session bound to the application database.
    """
    with get_session_factory()() as session:
        yield session

"""SQLAlchemy 2.x engine and session factory.

The same code runs on PostgreSQL 16 (Docker Compose) and SQLite (local
development and tests). Only the Encrypted Data Layer
(``app.storage.repository``, ARC-007) uses the sessions created here to write.
"""
from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import is_in_memory_sqlite
from app.models import Base


def _sqlite_enable_foreign_keys(dbapi_connection, _record) -> None:  # noqa: ANN001
    """SQLite ignores FOREIGN KEY constraints unless this pragma is set per connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def make_engine(database_url: str) -> Engine:
    """Create an engine; SQLite gets the options needed by FastAPI's thread pool.

    An in-memory SQLite database exists per connection, so it uses one shared
    connection (``StaticPool``) for all threads (development mode, see config.py).
    """
    if database_url.startswith("sqlite"):
        options: dict = {"connect_args": {"check_same_thread": False}}
        if is_in_memory_sqlite(database_url):
            options["poolclass"] = StaticPool
        engine = create_engine(database_url, **options)
        event.listen(engine, "connect", _sqlite_enable_foreign_keys)
        return engine
    return create_engine(database_url, pool_pre_ping=True)


class Database:
    """Owns the engine and hands out sessions."""

    def __init__(self, database_url: str) -> None:
        self.url = database_url
        self.engine = make_engine(database_url)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        """Create missing tables (called on application start-up).

        Schema migrations (Alembic) are not needed in Sprint 2; see
        docs/architecture/database-schema.md.
        """
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        """Return a new session; the caller closes it."""
        return self._session_factory()

    def dispose(self) -> None:
        """Close all pooled connections (application shut-down)."""
        self.engine.dispose()

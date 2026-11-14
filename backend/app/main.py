"""MediTrace API entry point.

Run locally from ``backend/``::

    uvicorn app.main:app --reload

or with PostgreSQL through ``docker compose up`` (repository root).
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.db import Database
from app.ingestion.router import AlarmSink, router as ingestion_router
from app.storage.crypto import DecryptionError, FieldCipher
from app.storage.repository import StoredReading

API_VERSION = "0.2.0"
logger = logging.getLogger("meditrace.api")


# Controls RISK-007
async def _decryption_failed(request: Request, exc: DecryptionError) -> JSONResponse:
    """Stored data failed GCM authentication: never return it, answer with a clear 500.

    Causes: modified ciphertext (tampering) or a different DATA_KEY than the one
    used to write the data. Sprint 3: also write an audit/hazard entry (ARC-006).
    """
    logger.error("decryption failed on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "stored data could not be decrypted (wrong DATA_KEY or tampered data)"},
    )


def _no_alarm_engine(_reading: StoredReading) -> None:
    """Placeholder sink for valid readings until the Alarm Engine is wired in.

    Sprint 3: replace with the AlarmEngine (ARC-003) entry point.
    """


def create_app(settings: Settings | None = None, alarm_sink: AlarmSink | None = None) -> FastAPI:
    """Build the FastAPI application (tests pass their own settings and sink)."""
    settings = settings or Settings.from_env()
    database = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        database.create_all()
        yield
        database.dispose()

    app = FastAPI(title="MediTrace", version=API_VERSION, lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.state.cipher = FieldCipher(settings.data_key)
    app.state.alarm_sink = alarm_sink or _no_alarm_engine
    app.add_exception_handler(DecryptionError, _decryption_failed)

    @app.get("/health")
    def health() -> dict:
        """Liveness check used by CI and Docker."""
        return {"status": "ok"}

    app.include_router(ingestion_router)
    return app


app = create_app()

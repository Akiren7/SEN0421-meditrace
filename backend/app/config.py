"""Runtime settings of the MediTrace backend, read from environment variables.

Variables
---------
``DATABASE_URL``
    SQLAlchemy URL. Default ``sqlite:///./meditrace.db`` when the keys are set
    (in-memory ``sqlite://`` when they are not, see below). Docker Compose uses
    ``postgresql+psycopg://...`` (PostgreSQL 16).
``DATA_KEY``
    Base64 of 32 random bytes: AES-256-GCM key of the Encrypted Data Layer
    (ARC-007, REQ-010).
``INDEX_KEY``
    Base64 of 32 random bytes: HMAC-SHA256 key of the patient-name blind index
    (PLN-05, ADR-001). Must differ from ``DATA_KEY`` (key separation).

Keys are never committed to the repository (REQ-010, acceptance criterion 5);
see ``.env.example`` for how to generate them.

Development mode: when *both* keys and ``DATABASE_URL`` are missing, the
backend starts with random per-run keys **and an in-memory database** and logs
a warning, so ``uvicorn app.main:app --reload`` works without set-up. Random
keys are never combined with a persistent database: after a restart (every
code change with ``--reload``) the old rows could not be decrypted any more
and re-pairing would fail. Missing keys with a persistent ``DATABASE_URL`` are
therefore a configuration error.
"""
from __future__ import annotations

import base64
import binascii
import logging
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass

logger = logging.getLogger("meditrace.config")

DEFAULT_DATABASE_URL = "sqlite:///./meditrace.db"
IN_MEMORY_DATABASE_URL = "sqlite://"
KEY_BYTES = 32  # AES-256 key length; also used for the HMAC key


def is_in_memory_sqlite(database_url: str) -> bool:
    """True for ``sqlite://`` / ``sqlite:///:memory:`` (data lives only in this process)."""
    url = database_url.strip()
    return url in ("sqlite://", "sqlite:///:memory:") or (
        url.startswith("sqlite") and "mode=memory" in url
    )


class ConfigError(ValueError):
    """Raised when a setting is present but unusable (e.g. wrong key length)."""


def generate_key() -> str:
    """Return a new random key in the format expected by ``DATA_KEY`` / ``INDEX_KEY``."""
    return base64.b64encode(secrets.token_bytes(KEY_BYTES)).decode("ascii")


def decode_key(name: str, value: str) -> bytes:
    """Decode a base64 key and check that it is exactly 32 bytes long."""
    try:
        key = base64.b64decode(value.strip(), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ConfigError(f"{name} is not valid base64") from exc
    if len(key) != KEY_BYTES:
        raise ConfigError(f"{name} must decode to {KEY_BYTES} bytes, got {len(key)}")
    return key


@dataclass(frozen=True)
class Settings:
    """Immutable settings object passed to :func:`app.main.create_app`."""

    database_url: str
    data_key: bytes
    index_key: bytes
    ephemeral_keys: bool = False

    def __post_init__(self) -> None:
        for name, key in (("DATA_KEY", self.data_key), ("INDEX_KEY", self.index_key)):
            if len(key) != KEY_BYTES:
                raise ConfigError(f"{name} must be {KEY_BYTES} bytes, got {len(key)}")
        if self.data_key == self.index_key:
            raise ConfigError("DATA_KEY and INDEX_KEY must be different keys")

    def __repr__(self) -> str:  # never print key material
        return (
            f"Settings(database_url={self.database_url!r}, data_key=<hidden>, "
            f"index_key=<hidden>, ephemeral_keys={self.ephemeral_keys})"
        )

    # Controls RISK-007
    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build settings from ``environ`` (default: ``os.environ``)."""
        env = os.environ if environ is None else environ
        configured_url = env.get("DATABASE_URL", "").strip()
        raw_data_key = env.get("DATA_KEY", "").strip()
        raw_index_key = env.get("INDEX_KEY", "").strip()

        if not raw_data_key and not raw_index_key:
            database_url = configured_url or IN_MEMORY_DATABASE_URL
            if not is_in_memory_sqlite(database_url):
                raise ConfigError(
                    "DATA_KEY and INDEX_KEY are required for a persistent DATABASE_URL "
                    "(random per-run keys would make stored data unreadable after a restart)"
                )
            logger.warning(
                "DATA_KEY and INDEX_KEY are not set: development mode with random keys and "
                "an in-memory database - all data is lost when the server stops or reloads. "
                "Set both keys (see .env.example) for persistent storage."
            )
            return cls(
                database_url=database_url,
                data_key=secrets.token_bytes(KEY_BYTES),
                index_key=secrets.token_bytes(KEY_BYTES),
                ephemeral_keys=True,
            )
        if not raw_data_key or not raw_index_key:
            missing = "DATA_KEY" if not raw_data_key else "INDEX_KEY"
            raise ConfigError(f"{missing} is not set (set both DATA_KEY and INDEX_KEY)")

        return cls(
            database_url=configured_url or DEFAULT_DATABASE_URL,
            data_key=decode_key("DATA_KEY", raw_data_key),
            index_key=decode_key("INDEX_KEY", raw_index_key),
        )

"""ORM models (database schema v1): Patient, Device, Reading, HazardEvent.

Columns ending in ``_enc`` hold AES-256-GCM ciphertext (``nonce || ciphertext
|| tag``) produced by ``app.storage.crypto`` (REQ-010). Only identifiers,
timestamps and the ``valid`` flag are stored in clear so that they can be
queried. Description and rationale: docs/architecture/database-schema.md.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

ID_LENGTH = 64


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Timestamp column that only accepts aware datetimes and always returns UTC.

    PostgreSQL stores ``timestamptz``; SQLite has no time zones and returns
    naive values, which are interpreted as UTC here. Naive input is rejected
    so that a local time can never be stored by mistake.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"naive datetime {value!r} cannot be stored; use UTC")
        value = value.astimezone(UTC)
        if dialect.name == "sqlite":
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Declarative base of all MediTrace tables."""


class Patient(Base):
    """A ward patient. The name is encrypted; ``name_index`` is the HMAC blind index."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    name_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    name_index: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)


class Device(Base):
    """A bedside device. ``patient_id`` is unique: one device <-> one patient (REQ-013)."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(ID_LENGTH), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        String(ID_LENGTH), ForeignKey("patients.id"), nullable=False, unique=True
    )
    paired_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)


class Reading(Base):
    """One vital-sign reading. HR/BP/SpO2 are stored as one encrypted JSON blob."""

    __tablename__ = "readings"
    __table_args__ = (Index("ix_readings_patient_time", "patient_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(
        String(ID_LENGTH), ForeignKey("patients.id"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(
        String(ID_LENGTH), ForeignKey("devices.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vitals_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class HazardEvent(Base):
    """Hazard log entry (ARC-004 v0). Field names follow the shared data contract.

    ``device_id`` has no foreign key on purpose: UNPAIRED_DEVICE events refer
    to devices that are not in the ``devices`` table. ``detail`` never contains
    vital-sign values (they stay encrypted in ``readings``).
    """

    __tablename__ = "hazard_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utc_now)
    patient_id: Mapped[str | None] = mapped_column(
        String(ID_LENGTH), ForeignKey("patients.id"), nullable=True
    )
    device_id: Mapped[str | None] = mapped_column(String(ID_LENGTH), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    risk_id: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")

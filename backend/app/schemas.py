"""Pydantic v2 request/response models (shared data contract, A6).

Timestamps are ISO 8601 and must carry a time zone; they are converted to UTC
on input and returned in UTC (``...Z``). Vital values are *not* range-checked
here: an out-of-range value is a valid request that produces an invalid
reading (REQ-002). Only malformed requests (missing fields, wrong types,
unknown fields, naive timestamps) are rejected with HTTP 422.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    StrictInt,
    StringConstraints,
    field_validator,
)

Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$"
    ),
]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PairRequest(_Strict):
    """``POST /devices/pair`` body."""

    device_id: Identifier
    patient_id: Identifier
    patient_name: PersonName


class PairResponse(BaseModel):
    """``POST /devices/pair`` response."""

    device_id: str
    patient_id: str
    status: Literal["paired", "already_paired"]


class ReadingIn(_Strict):
    """``POST /readings`` body: ``{device_id, timestamp, hr, sys_bp, dia_bp, spo2}``.

    ``extra="forbid"``: a device cannot send e.g. a ``patient_id`` and have it
    silently ignored; the patient comes only from the pairing (RISK-008).
    Vitals are strict integers: ``"72"``, ``72.5`` or ``true`` are malformed.
    """

    device_id: Identifier
    timestamp: AwareDatetime
    hr: StrictInt
    sys_bp: StrictInt
    dia_bp: StrictInt
    spo2: StrictInt

    @field_validator("timestamp")
    @classmethod
    def _to_utc(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    def vitals(self) -> dict[str, int]:
        """The four vital values as a dict."""
        return {"hr": self.hr, "sys_bp": self.sys_bp, "dia_bp": self.dia_bp, "spo2": self.spo2}


class IngestResponse(BaseModel):
    """``POST /readings`` response: ``accepted`` (valid) or ``invalid`` (REQ-002)."""

    status: Literal["accepted", "invalid"]


class ReadingOut(BaseModel):
    """Reading (out): ``{patient_id, device_id, timestamp, hr, sys_bp, dia_bp, spo2, valid}``."""

    patient_id: str
    device_id: str
    timestamp: datetime
    hr: int
    sys_bp: int
    dia_bp: int
    spo2: int
    valid: bool


class HazardEventOut(BaseModel):
    """HazardEvent contract; exposed by ``GET /hazards`` in Sprint 3."""

    id: int
    timestamp: datetime
    patient_id: str | None
    device_id: str | None
    event_type: str
    risk_id: str
    detail: str

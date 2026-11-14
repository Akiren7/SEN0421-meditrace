"""Data model of the Alarm Engine (ARC-003).

Pure Python: no FastAPI, no database. Field names follow the shared data
contract (vital names ``hr``/``sys_bp``/``dia_bp``/``spo2``, enum values in
upper case, timestamps timezone-aware UTC) so that Ingestion (ARC-002), the
persisted ``Alarm`` record (Sprint 3) and the dashboard (ARC-008) can map them
one to one.

All threshold numbers below are educational defaults, configurable per
patient - not clinical advice. Rationale: docs/risk/risk-register.md
("Threshold rationale").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

Number = int | float


class Priority(StrEnum):
    """IEC 60601-1-8 alarm priorities (REQ-005)."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlarmKind(StrEnum):
    """What caused the alarm event."""

    THRESHOLD = "THRESHOLD"
    DATA_LOSS = "DATA_LOSS"
    ARTEFACT_SUSPECTED = "ARTEFACT_SUSPECTED"


class AlarmState(StrEnum):
    """Life cycle of a persisted alarm.

    Not used by the engine core yet: the ``Alarm`` record with ``id`` and
    ``state`` (and acknowledgement, REQ-007) is added in Sprint 3.
    """

    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Vital(StrEnum):
    """Vital-sign names, identical to the reading field names."""

    HR = "hr"
    SYS_BP = "sys_bp"
    DIA_BP = "dia_bp"
    SPO2 = "spo2"


def require_utc_aware(value: datetime, name: str) -> None:
    """Reject naive datetimes: the data contract uses timezone-aware UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware (UTC), got {value!r}")


@dataclass(frozen=True)
class VitalReading:
    """One validated reading of one patient (output of ARC-002).

    The engine assumes the reading already passed the REQ-002 plausibility
    check and the REQ-013 pairing check in Ingestion & Validation.
    """

    patient_id: str
    device_id: str
    timestamp: datetime
    hr: int
    sys_bp: int
    dia_bp: int
    spo2: int

    def __post_init__(self) -> None:
        require_utc_aware(self.timestamp, "timestamp")

    def value(self, vital: Vital) -> int:
        """Return the value of ``vital`` in this reading."""
        return int(getattr(self, vital.value))


@dataclass(frozen=True)
class Limit:
    """A low/high limit pair. ``None`` means "no limit on that side".

    A value equal to a limit is normal; only strictly ``<`` low or ``>`` high
    is a violation (shared boundary rule, A6).
    """

    low: Number | None = None
    high: Number | None = None

    def __post_init__(self) -> None:
        if self.low is not None and self.high is not None and self.low >= self.high:
            raise ValueError(f"low limit {self.low} must be below high limit {self.high}")

    def violated_by(self, value: Number) -> bool:
        """True when ``value`` is strictly outside the limits."""
        if self.low is not None and value < self.low:
            return True
        return self.high is not None and value > self.high


@dataclass(frozen=True)
class VitalThresholds:
    """Non-critical and critical limits for one vital sign.

    Non-critical violation -> MEDIUM after confirmation (REQ-015).
    Critical violation -> immediate HIGH (REQ-015 critical bypass).
    """

    non_critical: Limit = field(default_factory=Limit)
    critical: Limit = field(default_factory=Limit)

    def __post_init__(self) -> None:
        # A critical limit must be at least as extreme as the non-critical
        # one, otherwise a typo could create a "critical" band inside the
        # normal range. Fails loudly instead of alarming wrongly (RISK-004).
        nc, cr = self.non_critical, self.critical
        if nc.low is not None and cr.low is not None and cr.low > nc.low:
            raise ValueError(f"critical low {cr.low} must be <= non-critical low {nc.low}")
        if nc.high is not None and cr.high is not None and cr.high < nc.high:
            raise ValueError(f"critical high {cr.high} must be >= non-critical high {nc.high}")


def _default_hr() -> VitalThresholds:
    return VitalThresholds(non_critical=Limit(low=50, high=120), critical=Limit(low=40, high=150))


def _default_sys_bp() -> VitalThresholds:
    # No critical bypass for blood pressure in v1 (see threshold rationale).
    return VitalThresholds(non_critical=Limit(low=90, high=180))


def _default_dia_bp() -> VitalThresholds:
    # No default diastolic limits in v1; a Doctor may set them per patient.
    return VitalThresholds()


def _default_spo2() -> VitalThresholds:
    return VitalThresholds(non_critical=Limit(low=92), critical=Limit(low=85))


@dataclass(frozen=True)
class Thresholds:
    """Alarm thresholds of one patient (defaults from A6, override per patient).

    Changing them is Doctor-only (REQ-006, enforced by ARC-005 in Sprint 3).
    """

    hr: VitalThresholds = field(default_factory=_default_hr)
    sys_bp: VitalThresholds = field(default_factory=_default_sys_bp)
    dia_bp: VitalThresholds = field(default_factory=_default_dia_bp)
    spo2: VitalThresholds = field(default_factory=_default_spo2)

    def for_vital(self, vital: Vital) -> VitalThresholds:
        """Return the thresholds of ``vital``."""
        return getattr(self, vital.value)


@dataclass(frozen=True)
class ArtefactLimits:
    """Rate-of-change limits of RCM-002b (RISK-002).

    A change between two consecutive readings (at most ``max_gap`` apart)
    larger than these limits is treated as a suspected artefact.
    """

    hr_max_change: Number = 60  # bpm between consecutive readings, either direction
    spo2_max_drop: Number = 15  # percentage points, drops only
    max_gap: timedelta = timedelta(seconds=2)


@dataclass(frozen=True)
class AlarmEvent:
    """An alarm event emitted by the engine.

    Subset of the shared ``Alarm`` contract; ``id``, ``state``,
    ``acknowledged_by`` and ``acknowledged_at`` are added when the alarm is
    persisted in Sprint 3.
    """

    patient_id: str
    kind: AlarmKind
    vital: Vital | None
    priority: Priority
    value: Number | None
    timestamp: datetime
    risk_id: str

    def to_dict(self) -> dict:
        """JSON-ready dict using the shared contract field names."""
        return {
            "patient_id": self.patient_id,
            "kind": self.kind.value,
            "vital": self.vital.value if self.vital is not None else None,
            "priority": self.priority.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "risk_id": self.risk_id,
        }

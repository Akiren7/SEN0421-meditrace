"""Alarm Engine (ARC-003): thresholds, smart validation, artefact and data-loss alarms."""
from .engine import CONFIRMATION_READINGS, DATA_LOSS_TIMEOUT, AlarmEngine
from .models import (
    AlarmEvent,
    AlarmKind,
    AlarmState,
    ArtefactLimits,
    Limit,
    Priority,
    Thresholds,
    Vital,
    VitalReading,
    VitalThresholds,
)

__all__ = [
    "CONFIRMATION_READINGS",
    "DATA_LOSS_TIMEOUT",
    "AlarmEngine",
    "AlarmEvent",
    "AlarmKind",
    "AlarmState",
    "ArtefactLimits",
    "Limit",
    "Priority",
    "Thresholds",
    "Vital",
    "VitalReading",
    "VitalThresholds",
]

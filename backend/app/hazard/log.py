"""Minimal Hazard Log writer (ARC-004 v0), used by Ingestion & Validation.

Every hazardous event gets exactly one record with the fields of the shared
``HazardEvent`` contract: ``id, timestamp, patient_id|null, device_id|null,
event_type, risk_id, detail``. The RISK ID is derived from the event type
(mapping in A6 / SRS section 2.5), so a caller cannot attach the wrong risk.

Sprint 3 (ARC-004 complete): ``GET /hazards`` for Doctor/Auditor, DATA_LOSS
and ARTEFACT_SUSPECTED events from the Alarm Engine, AUTH_FAILURE from ARC-005.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from app.storage.repository import HazardEventRecord, Repository


class HazardEventType(StrEnum):
    """Hazard event types of the shared data contract."""

    IMPLAUSIBLE_VALUE = "IMPLAUSIBLE_VALUE"
    UNPAIRED_DEVICE = "UNPAIRED_DEVICE"
    DATA_LOSS = "DATA_LOSS"
    ARTEFACT_SUSPECTED = "ARTEFACT_SUSPECTED"
    AUTH_FAILURE = "AUTH_FAILURE"


EVENT_RISK: dict[HazardEventType, str] = {
    HazardEventType.IMPLAUSIBLE_VALUE: "RISK-002",
    HazardEventType.UNPAIRED_DEVICE: "RISK-008",
    HazardEventType.DATA_LOSS: "RISK-001",
    HazardEventType.ARTEFACT_SUSPECTED: "RISK-002",
    HazardEventType.AUTH_FAILURE: "RISK-006",
}


# Implements REQ-012
class HazardLog:
    """Writes hazard events through the Encrypted Data Layer (ARC-007)."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def record(
        self,
        event_type: HazardEventType,
        *,
        detail: str,
        patient_id: str | None = None,
        device_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> HazardEventRecord:
        """Append one hazard event; ``risk_id`` comes from :data:`EVENT_RISK`.

        ``detail`` must not contain vital-sign values or patient names: those
        are health data and stay encrypted (REQ-010). Refer to the reading by
        its ID instead.
        """
        event_type = HazardEventType(event_type)
        return self._repository.add_hazard_event(
            event_type=event_type.value,
            risk_id=EVENT_RISK[event_type],
            detail=detail,
            patient_id=patient_id,
            device_id=device_id,
            timestamp=timestamp,
        )

"""HTTP API of Ingestion & Validation (ARC-002).

Sprint 2 endpoints: ``POST /devices/pair``, ``POST /readings``,
``GET /patients/{patient_id}/readings``.

Sprint 3 hooks (not implemented yet, marked below): role checks through
ARC-005 (REQ-009), audit entries through ARC-006 (REQ-011), forwarding of
valid readings to the Alarm Engine ARC-003 (REQ-015).
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.hazard.log import HazardEventType, HazardLog
from app.ingestion.validation import check_pairing, check_plausibility
from app.schemas import IngestResponse, PairRequest, PairResponse, ReadingIn, ReadingOut
from app.storage.repository import PairingConflict, PairOutcome, Repository, StoredReading

router = APIRouter(tags=["ingestion"])

MAX_READINGS_LIMIT = 86_400  # 24 h at 1 reading/s (REQ-014)

AlarmSink = Callable[[StoredReading], None]


def get_repository(request: Request) -> Iterator[Repository]:
    """One session (unit of work) per request; uncommitted work is rolled back on close."""
    session = request.app.state.database.session()
    try:
        yield Repository(session, request.app.state.cipher, request.app.state.settings.index_key)
    finally:
        session.close()


RepositoryDep = Annotated[Repository, Depends(get_repository)]


# Implements REQ-013
# Controls RISK-008
@router.post("/devices/pair", response_model=PairResponse)
def pair_device(body: PairRequest, repo: RepositoryDep, response: Response) -> PairResponse:
    """Pair one device with exactly one patient (creates the patient if needed).

    201 new pairing · 200 same pairing again (idempotent) · 409 conflict with
    an existing pairing (the existing pairing is left unchanged).
    """
    # Sprint 3: require role Admin (ARC-005, REQ-009) and write an audit entry (ARC-006, REQ-011)
    try:
        outcome = repo.pair_device(body.device_id, body.patient_id, body.patient_name)
    except PairingConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    repo.commit()
    response.status_code = (
        status.HTTP_201_CREATED if outcome is PairOutcome.PAIRED else status.HTTP_200_OK
    )
    return PairResponse(device_id=body.device_id, patient_id=body.patient_id, status=outcome.value)


# Implements REQ-001, REQ-002, REQ-010, REQ-013
# Controls RISK-002, RISK-008
@router.post("/readings", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_reading(body: ReadingIn, repo: RepositoryDep, request: Request) -> IngestResponse:
    """Validate and store one reading.

    1. Unpaired device -> 422, reading not stored, hazard UNPAIRED_DEVICE (RISK-008).
    2. Implausible values -> stored with ``valid = false``, ``{"status": "invalid"}``,
       hazard IMPLAUSIBLE_VALUE (RISK-002), never forwarded to the Alarm Engine.
    3. Otherwise -> stored encrypted, ``{"status": "accepted"}``.
    """
    hazard_log = HazardLog(repo)

    patient_id = check_pairing(repo, body.device_id)
    if patient_id is None:
        hazard_log.record(
            HazardEventType.UNPAIRED_DEVICE,
            device_id=body.device_id,
            detail="reading rejected: device is not paired with a patient",
        )
        repo.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"device {body.device_id} is not paired with a patient",
        )

    vitals = body.vitals()
    plausibility = check_plausibility(vitals)
    reading_id = repo.add_reading(
        patient_id=patient_id,
        device_id=body.device_id,
        timestamp=body.timestamp,
        vitals=vitals,
        valid=plausibility.valid,
    )

    if not plausibility.valid:
        hazard_log.record(
            HazardEventType.IMPLAUSIBLE_VALUE,
            patient_id=patient_id,
            device_id=body.device_id,
            detail=f"reading {reading_id} marked invalid: " + "; ".join(plausibility.reasons),
        )
        repo.commit()
        return IngestResponse(status="invalid")  # invalid readings never reach the Alarm Engine

    repo.commit()
    stored = StoredReading(
        id=reading_id,
        patient_id=patient_id,
        device_id=body.device_id,
        timestamp=body.timestamp,
        valid=True,
        **vitals,
    )
    # Sprint 3: pass valid reading to AlarmEngine (ARC-003)
    alarm_sink: AlarmSink = request.app.state.alarm_sink
    alarm_sink(stored)
    return IngestResponse(status="accepted")


@router.get("/patients/{patient_id}/readings", response_model=list[ReadingOut])
def list_readings(
    patient_id: str,
    repo: RepositoryDep,
    limit: Annotated[int, Query(ge=1, le=MAX_READINGS_LIMIT)] = 100,
) -> list[ReadingOut]:
    """Decrypted readings of one patient, newest first (dashboard, REQ-014)."""
    # Sprint 3: require role Doctor/Nurse (ARC-005, REQ-009) and audit the access (ARC-006, REQ-011)
    if not repo.patient_exists(patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown patient")
    return [
        ReadingOut(
            patient_id=r.patient_id,
            device_id=r.device_id,
            timestamp=r.timestamp,
            hr=r.hr,
            sys_bp=r.sys_bp,
            dia_bp=r.dia_bp,
            spo2=r.spo2,
            valid=r.valid,
        )
        for r in repo.list_readings(patient_id, limit)
    ]

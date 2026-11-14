"""Encrypted Data Layer (ARC-007) - the ONLY code that writes to the database.

Design decision 2 (A6): every other component (ingestion, hazard log, later
auth/audit) calls this repository instead of touching SQLAlchemy sessions, so
encryption cannot be bypassed. The repository encrypts on write, decrypts on
read and returns plain dataclasses, never ORM objects with ciphertext.

Transactions: methods only ``flush``; the caller ends the unit of work with
:meth:`Repository.commit` (or the session is rolled back when it is closed).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Device, HazardEvent, Patient, Reading, utc_now
from app.storage.crypto import FieldCipher, blind_index

VITAL_FIELDS: tuple[str, ...] = ("hr", "sys_bp", "dia_bp", "spo2")


class PairingConflict(Exception):
    """Pairing would break the 1:1 device-patient rule (REQ-013) -> HTTP 409."""


class PairOutcome(StrEnum):
    """Result of :meth:`Repository.pair_device`."""

    PAIRED = "paired"
    ALREADY_PAIRED = "already_paired"


@dataclass(frozen=True)
class PatientRecord:
    """Decrypted patient."""

    id: str
    name: str


@dataclass(frozen=True)
class StoredReading:
    """Decrypted reading; field names follow the shared data contract (A6)."""

    id: int
    patient_id: str
    device_id: str
    timestamp: datetime
    hr: int
    sys_bp: int
    dia_bp: int
    spo2: int
    valid: bool


@dataclass(frozen=True)
class HazardEventRecord:
    """Hazard log entry as stored (contract: HazardEvent, A6)."""

    id: int
    timestamp: datetime
    patient_id: str | None
    device_id: str | None
    event_type: str
    risk_id: str
    detail: str


def _name_aad(patient_id: str) -> bytes:
    """Associated data binding an encrypted name to its patient row."""
    return f"patients.name|{patient_id}".encode()


def _vitals_aad(patient_id: str, device_id: str) -> bytes:
    """Associated data binding encrypted vitals to their patient and device."""
    return f"readings.vitals|{patient_id}|{device_id}".encode()


# Implements REQ-010
# Controls RISK-007
class Repository:
    """Encrypting repository over one SQLAlchemy session."""

    def __init__(self, session: Session, cipher: FieldCipher, index_key: bytes) -> None:
        self._session = session
        self._cipher = cipher
        self._index_key = index_key

    # -- transactions -----------------------------------------------------
    def commit(self) -> None:
        """Commit the current unit of work."""
        self._session.commit()

    def rollback(self) -> None:
        """Discard the current unit of work."""
        self._session.rollback()

    # -- patients and devices ---------------------------------------------
    def _to_patient_record(self, patient: Patient) -> PatientRecord:
        name = self._cipher.decrypt_text(patient.name_enc, _name_aad(patient.id))
        return PatientRecord(id=patient.id, name=name)

    def patient_exists(self, patient_id: str) -> bool:
        """True if the patient is registered (no decryption needed)."""
        return self._session.get(Patient, patient_id) is not None

    def get_patient(self, patient_id: str) -> PatientRecord | None:
        """Return the decrypted patient or ``None``."""
        patient = self._session.get(Patient, patient_id)
        return None if patient is None else self._to_patient_record(patient)

    # Implements REQ-010
    def find_patient_by_name(self, name: str) -> list[PatientRecord]:
        """Exact-match search through the HMAC blind index (ADR-001, closes RSK-06).

        Only rows whose index equals ``HMAC(INDEX_KEY, normalize_name(name))``
        are read and decrypted; partial names do not match.
        """
        index = blind_index(self._index_key, name)
        rows = self._session.scalars(
            select(Patient).where(Patient.name_index == index).order_by(Patient.id)
        )
        return [self._to_patient_record(row) for row in rows]

    def get_device_patient(self, device_id: str) -> str | None:
        """Return the patient ID paired with ``device_id`` or ``None`` if unpaired."""
        device = self._session.get(Device, device_id)
        return None if device is None else device.patient_id

    # Implements REQ-013
    # Controls RISK-008
    def pair_device(self, device_id: str, patient_id: str, patient_name: str) -> PairOutcome:
        """Pair ``device_id`` with ``patient_id`` (1:1), creating the patient if needed.

        Raises :class:`PairingConflict` when the device is paired with another
        patient, the patient already has another device, or ``patient_id`` is
        registered under a different name. Pairing the same device with the
        same patient again is idempotent.
        """
        name_index = blind_index(self._index_key, patient_name)
        patient = self._session.get(Patient, patient_id)
        if patient is not None and patient.name_index != name_index:
            raise PairingConflict(f"patient {patient_id} is registered with a different name")

        device = self._session.get(Device, device_id)
        if device is not None:
            if device.patient_id == patient_id:
                return PairOutcome.ALREADY_PAIRED
            raise PairingConflict(f"device {device_id} is already paired with another patient")

        other_device = self._session.scalar(select(Device).where(Device.patient_id == patient_id))
        if other_device is not None:
            raise PairingConflict(
                f"patient {patient_id} already has device {other_device.id} (1:1 pairing)"
            )

        try:
            if patient is None:
                self._session.add(
                    Patient(
                        id=patient_id,
                        name_enc=self._cipher.encrypt_text(patient_name, _name_aad(patient_id)),
                        name_index=name_index,
                    )
                )
                # The models define no relationship(), so the unit of work does not
                # order INSERTs by foreign key: flush the patient before its device.
                self._session.flush()
            self._session.add(Device(id=device_id, patient_id=patient_id))
            self._session.flush()
        except IntegrityError as exc:
            # Only a concurrent request pairing the same device/patient can get here,
            # because all conflicts were checked above.
            self._session.rollback()
            raise PairingConflict("pairing conflicts with a concurrent pairing") from exc
        return PairOutcome.PAIRED

    # -- readings -----------------------------------------------------------
    def add_reading(
        self,
        *,
        patient_id: str,
        device_id: str,
        timestamp: datetime,
        vitals: Mapping[str, int],
        valid: bool,
    ) -> int:
        """Store one reading with encrypted vitals; return its database ID."""
        payload = {name: vitals[name] for name in VITAL_FIELDS}
        row = Reading(
            patient_id=patient_id,
            device_id=device_id,
            timestamp=timestamp,
            valid=valid,
            vitals_enc=self._cipher.encrypt_json(payload, _vitals_aad(patient_id, device_id)),
        )
        self._session.add(row)
        self._session.flush()
        return row.id

    def list_readings(self, patient_id: str, limit: int) -> list[StoredReading]:
        """Return the newest ``limit`` readings of a patient, decrypted, newest first."""
        rows = self._session.scalars(
            select(Reading)
            .where(Reading.patient_id == patient_id)
            .order_by(Reading.timestamp.desc(), Reading.id.desc())
            .limit(limit)
        )
        readings = []
        for row in rows:
            vitals = self._cipher.decrypt_json(
                row.vitals_enc, _vitals_aad(row.patient_id, row.device_id)
            )
            readings.append(
                StoredReading(
                    id=row.id,
                    patient_id=row.patient_id,
                    device_id=row.device_id,
                    timestamp=row.timestamp,
                    valid=row.valid,
                    **{name: vitals[name] for name in VITAL_FIELDS},
                )
            )
        return readings

    def count_readings(self) -> int:
        """Number of stored readings (used by tests and the simulator summary)."""
        return self._session.scalar(select(func.count()).select_from(Reading)) or 0

    # -- hazard log ---------------------------------------------------------
    def add_hazard_event(
        self,
        *,
        event_type: str,
        risk_id: str,
        detail: str,
        patient_id: str | None = None,
        device_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> HazardEventRecord:
        """Append a hazard event (written by ``app.hazard.log`` only)."""
        row = HazardEvent(
            timestamp=timestamp or utc_now(),
            patient_id=patient_id,
            device_id=device_id,
            event_type=event_type,
            risk_id=risk_id,
            detail=detail,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_hazard_record(row)

    def list_hazard_events(self) -> list[HazardEventRecord]:
        """All hazard events in insertion order (GET /hazards follows in Sprint 3)."""
        rows = self._session.scalars(select(HazardEvent).order_by(HazardEvent.id))
        return [self._to_hazard_record(row) for row in rows]

    @staticmethod
    def _to_hazard_record(row: HazardEvent) -> HazardEventRecord:
        return HazardEventRecord(
            id=row.id,
            timestamp=row.timestamp,
            patient_id=row.patient_id,
            device_id=row.device_id,
            event_type=row.event_type,
            risk_id=row.risk_id,
            detail=row.detail,
        )

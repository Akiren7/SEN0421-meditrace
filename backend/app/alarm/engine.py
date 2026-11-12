"""Alarm Engine core (ARC-003) - IEEE 1012 integrity level 3.

Pure Python, independent of FastAPI and the database, so that Ingestion &
Validation (ARC-002) can call it directly in Sprint 3:

* ``process(reading)`` for every reading that passed the REQ-002 / REQ-013
  checks, in timestamp order per patient;
* ``check_data_loss(now)`` periodically (planned: once per second).

The engine keeps a small in-memory state per patient and per vital so that an
alarm is raised once per episode and not re-raised every second. It is not
thread-safe; Sprint 3 calls it from a single event loop.

Sprint 3 hooks (not implemented now, see docs/risk/risk-register.md):

* REQ-007 / RCM-005: ``acknowledge(...)``; persisted ``Alarm`` records with
  ``state`` ACTIVE -> ACKNOWLEDGED -> RESOLVED. A HIGH alarm must then stay
  active until acknowledged even if the condition clears.
* RCM-005b: ``check_escalation(now)`` re-alerts a HIGH alarm that is still
  unacknowledged after 60 s (decision recorded in the risk register).
* REQ-003 / REQ-013: register a patient at device pairing so data loss is
  also detected before the first reading arrives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import (
    AlarmEvent,
    AlarmKind,
    ArtefactLimits,
    Priority,
    Thresholds,
    Vital,
    VitalReading,
    VitalThresholds,
    require_utc_aware,
)

CONFIRMATION_READINGS = 5
"""REQ-015: consecutive valid violating readings needed for a MEDIUM alarm."""

DATA_LOSS_TIMEOUT = timedelta(seconds=10)
"""REQ-003: silence after which a DATA_LOSS alarm is raised (``>=``)."""

RISK_DATA_LOSS = "RISK-001"
RISK_ARTEFACT = "RISK-002"
RISK_SMART_VALIDATION = "RISK-005"
RISK_CRITICAL_BYPASS = "RISK-009"


@dataclass
class _VitalState:
    """Smart-validation state of one vital of one patient."""

    consecutive_violations: int = 0
    raised: Priority | None = None  # priority already raised in this episode


@dataclass
class _PatientState:
    """Everything the engine remembers about one patient."""

    last_reading: VitalReading
    data_loss_raised: bool = False
    vitals: dict[Vital, _VitalState] = field(
        default_factory=lambda: {vital: _VitalState() for vital in Vital}
    )


class AlarmEngine:
    """Threshold, smart-validation, artefact and data-loss logic."""

    def __init__(
        self,
        default_thresholds: Thresholds | None = None,
        artefact_limits: ArtefactLimits | None = None,
        confirmation_readings: int = CONFIRMATION_READINGS,
        data_loss_timeout: timedelta = DATA_LOSS_TIMEOUT,
    ) -> None:
        if confirmation_readings < 1:
            raise ValueError("confirmation_readings must be at least 1")
        if data_loss_timeout <= timedelta(0):
            raise ValueError("data_loss_timeout must be positive")
        self._default_thresholds = default_thresholds or Thresholds()
        self._artefact_limits = artefact_limits or ArtefactLimits()
        self._confirmation_readings = confirmation_readings
        self._data_loss_timeout = data_loss_timeout
        self._thresholds: dict[str, Thresholds] = {}
        self._patients: dict[str, _PatientState] = {}

    # ------------------------------------------------------------------
    # Thresholds
    # ------------------------------------------------------------------

    # Not tagged "Implements REQ-006" on purpose: the Doctor-only check and the
    # audit entry (REQ-006, RISK-004) are enforced by ARC-005 / ARC-006 in
    # Sprint 3. Tagging it here would let the compliance report show REQ-006
    # as covered before it is (RISK-010).
    def set_thresholds(self, patient_id: str, thresholds: Thresholds) -> None:
        """Override the thresholds of one patient.

        Only a Doctor may call this through the API (REQ-006). The
        smart-validation counters are kept, so a change never delays an alarm
        that is already being confirmed.
        """
        self._thresholds[patient_id] = thresholds

    def thresholds_for(self, patient_id: str) -> Thresholds:
        """Return the patient's override, or the default thresholds."""
        return self._thresholds.get(patient_id, self._default_thresholds)

    # ------------------------------------------------------------------
    # Readings
    # ------------------------------------------------------------------

    # Implements REQ-015, REQ-005
    # Controls RISK-005, RISK-009, RISK-002
    def process(self, reading: VitalReading) -> list[AlarmEvent]:
        """Evaluate one validated reading and return the new alarm events."""
        state = self._patients.get(reading.patient_id)
        if state is None:
            state = _PatientState(last_reading=reading)
            self._patients[reading.patient_id] = state
            previous = None
        else:
            previous = state.last_reading
            state.last_reading = reading
        state.data_loss_raised = False  # data has returned (REQ-003)

        thresholds = self.thresholds_for(reading.patient_id)
        events: list[AlarmEvent] = []
        for vital in Vital:
            events.extend(
                self._evaluate_vital(
                    reading, previous, vital, thresholds.for_vital(vital), state.vitals[vital]
                )
            )
        return events

    def _evaluate_vital(
        self,
        reading: VitalReading,
        previous: VitalReading | None,
        vital: Vital,
        limits: VitalThresholds,
        state: _VitalState,
    ) -> list[AlarmEvent]:
        value = reading.value(vital)
        critical = limits.critical.violated_by(value)
        violating = critical or limits.non_critical.violated_by(value)
        artefact = self._is_suspected_artefact(vital, reading, previous)
        events: list[AlarmEvent] = []

        # RCM-002b: report the suspected artefact as a LOW informational event.
        if artefact:
            events.append(
                self._event(reading, AlarmKind.ARTEFACT_SUSPECTED, vital, Priority.LOW, RISK_ARTEFACT)
            )

        # REQ-015 critical bypass (RCM-009): a critical value alarms at once,
        # even when it is also a suspected artefact - RCM-002b must never mask
        # a critical alarm (ISO 14971 7.5).
        if critical and state.raised is not Priority.HIGH:
            events.append(
                self._event(reading, AlarmKind.THRESHOLD, vital, Priority.HIGH, RISK_CRITICAL_BYPASS)
            )
            state.raised = Priority.HIGH

        # RCM-002b: a suspected artefact neither counts toward the
        # confirmation window nor ends an episode.
        if artefact:
            return events

        if not violating:
            # Normal value: reset the window, the episode is over.
            state.consecutive_violations = 0
            state.raised = None
            return events

        # REQ-015 smart validation (RCM-005): MEDIUM only after N consecutive
        # valid violating readings.
        state.consecutive_violations += 1
        if state.consecutive_violations >= self._confirmation_readings and state.raised is None:
            events.append(
                self._event(reading, AlarmKind.THRESHOLD, vital, Priority.MEDIUM, RISK_SMART_VALIDATION)
            )
            state.raised = Priority.MEDIUM
        return events

    # Implements REQ-002 (RCM-002b rate-of-change part; the range check is in ARC-002)
    # Controls RISK-002
    def _is_suspected_artefact(
        self, vital: Vital, reading: VitalReading, previous: VitalReading | None
    ) -> bool:
        """True when the change from the previous reading is not physiological.

        The reference is always the immediately previous reading, even if that
        one was itself flagged. A real step change is therefore flagged for
        one reading only and counts from the next reading on (worst-case extra
        delay of a MEDIUM alarm: one reading).
        """
        if previous is None:
            return False
        gap = reading.timestamp - previous.timestamp
        if not timedelta(0) < gap <= self._artefact_limits.max_gap:
            return False  # no usable reference (first reading after a gap)
        change = reading.value(vital) - previous.value(vital)
        if vital is Vital.HR:
            return abs(change) > self._artefact_limits.hr_max_change
        if vital is Vital.SPO2:
            return -change > self._artefact_limits.spo2_max_drop
        return False

    # ------------------------------------------------------------------
    # Data loss
    # ------------------------------------------------------------------

    # Implements REQ-003
    # Controls RISK-001
    def check_data_loss(self, now: datetime) -> list[AlarmEvent]:
        """Raise one DATA_LOSS HIGH alarm per silent patient.

        A patient is silent when ``now - last reading >= 10 s``. The alarm is
        raised once and raised again only after data has returned and stopped
        again.
        """
        require_utc_aware(now, "now")
        events: list[AlarmEvent] = []
        for patient_id, state in self._patients.items():
            if state.data_loss_raised:
                continue
            if now - state.last_reading.timestamp >= self._data_loss_timeout:
                events.append(
                    AlarmEvent(
                        patient_id=patient_id,
                        kind=AlarmKind.DATA_LOSS,
                        vital=None,
                        priority=Priority.HIGH,
                        value=None,
                        timestamp=now,
                        risk_id=RISK_DATA_LOSS,
                    )
                )
                state.data_loss_raised = True
        return events

    # ------------------------------------------------------------------
    # Read-only state (tests, Sprint 3 wiring)
    # ------------------------------------------------------------------

    def current_priority(self, patient_id: str, vital: Vital) -> Priority | None:
        """Priority of the alarm raised in the current episode, if any."""
        state = self._patients.get(patient_id)
        return state.vitals[vital].raised if state is not None else None

    def data_loss_active(self, patient_id: str) -> bool:
        """True while a DATA_LOSS alarm is raised for the patient."""
        state = self._patients.get(patient_id)
        return state is not None and state.data_loss_raised

    @staticmethod
    def _event(
        reading: VitalReading, kind: AlarmKind, vital: Vital, priority: Priority, risk_id: str
    ) -> AlarmEvent:
        return AlarmEvent(
            patient_id=reading.patient_id,
            kind=kind,
            vital=vital,
            priority=priority,
            value=reading.value(vital),
            timestamp=reading.timestamp,
            risk_id=risk_id,
        )

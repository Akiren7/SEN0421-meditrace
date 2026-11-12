"""Unit tests for the Alarm Engine core (ARC-003, IEEE 1012 integrity level 3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from datetime import UTC, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402

from app.alarm import (  # noqa: E402
    AlarmEngine,
    AlarmEvent,
    AlarmKind,
    ArtefactLimits,
    Limit,
    Priority,
    Thresholds,
    Vital,
    VitalReading,
    VitalThresholds,
)

T0 = datetime(2026, 11, 10, 8, 0, 0, tzinfo=UTC)
NORMAL = {"hr": 75, "sys_bp": 120, "dia_bp": 80, "spo2": 97}


def reading(second: float, patient_id: str = "P-001", **vitals: int) -> VitalReading:
    """Build a reading ``second`` seconds after T0; unspecified vitals are normal."""
    values = {**NORMAL, **vitals}
    return VitalReading(
        patient_id=patient_id,
        device_id=f"DEV-{patient_id}",
        timestamp=T0 + timedelta(seconds=second),
        **values,
    )


def feed(engine: AlarmEngine, readings: list[VitalReading]) -> list[list[AlarmEvent]]:
    """Process readings in order and return the events of each one."""
    return [engine.process(r) for r in readings]


def series(vital: str, values: list[int], start: int = 0, patient_id: str = "P-001") -> list[VitalReading]:
    """One reading per second with ``vital`` taking the given values."""
    return [reading(start + i, patient_id, **{vital: v}) for i, v in enumerate(values)]


# ---------------------------------------------------------------------------
# REQ-015 smart validation (RCM-005)
# ---------------------------------------------------------------------------


def test_four_violations_no_alarm_fifth_gives_one_medium():
    """TC-015 / REQ-015: 4 consecutive non-critical violations give no alarm, the 5th gives one MEDIUM."""
    engine = AlarmEngine()
    events = feed(engine, series("spo2", [90] * 5))

    assert events[:4] == [[], [], [], []]
    assert events[4] == [
        AlarmEvent(
            patient_id="P-001",
            kind=AlarmKind.THRESHOLD,
            vital=Vital.SPO2,
            priority=Priority.MEDIUM,
            value=90,
            timestamp=T0 + timedelta(seconds=4),
            risk_id="RISK-005",
        )
    ]


def test_medium_alarm_is_raised_once_per_episode():
    """TC-015 / REQ-015: a persisting violation does not re-raise the MEDIUM alarm every second."""
    engine = AlarmEngine()
    events = feed(engine, series("hr", [125] * 12))

    flat = [e for per_reading in events for e in per_reading]
    assert len(flat) == 1
    assert flat[0].priority is Priority.MEDIUM
    assert engine.current_priority("P-001", Vital.HR) is Priority.MEDIUM


def test_normal_reading_resets_the_counter():
    """TC-015 / REQ-015: a normal reading between violations resets the consecutive-reading counter."""
    engine = AlarmEngine()
    events = feed(engine, series("sys_bp", [85, 85, 85, 85, 110, 85, 85, 85, 85]))
    assert all(e == [] for e in events)

    assert [e.priority for e in engine.process(reading(9, sys_bp=85))] == [Priority.MEDIUM]


def test_alarm_can_be_raised_again_after_values_return_to_normal():
    """TC-015 / REQ-015: after a normal reading ends the episode, a new episode raises a new alarm."""
    engine = AlarmEngine()
    feed(engine, series("hr", [45] * 5))
    assert engine.current_priority("P-001", Vital.HR) is Priority.MEDIUM

    assert engine.process(reading(5, hr=60)) == []
    assert engine.current_priority("P-001", Vital.HR) is None

    events = feed(engine, series("hr", [45] * 5, start=6))
    assert [e.priority for per in events for e in per] == [Priority.MEDIUM]


def test_vitals_are_confirmed_independently():
    """TC-015 / REQ-015: each vital has its own counter and alarm state."""
    engine = AlarmEngine()
    readings = [reading(i, hr=125, spo2=90) for i in range(5)]
    events = feed(engine, readings)

    assert [(e.vital, e.priority) for e in events[4]] == [
        (Vital.HR, Priority.MEDIUM),
        (Vital.SPO2, Priority.MEDIUM),
    ]


def test_confirmation_count_is_configurable():
    """TC-015 / REQ-015: the confirmation window length is a parameter (default 5)."""
    engine = AlarmEngine(confirmation_readings=2)
    events = feed(engine, series("spo2", [90, 90]))
    assert events[0] == []
    assert [e.priority for e in events[1]] == [Priority.MEDIUM]


# ---------------------------------------------------------------------------
# REQ-015 critical bypass (RCM-009)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("vital", "value"), [("spo2", 82), ("hr", 151), ("hr", 39)])
def test_critical_value_gives_immediate_high(vital, value):
    """TC-015 / REQ-015: one critical value (e.g. SpO2 82 %) gives an immediate HIGH alarm."""
    engine = AlarmEngine()
    events = engine.process(reading(0, **{vital: value}))

    assert events == [
        AlarmEvent(
            patient_id="P-001",
            kind=AlarmKind.THRESHOLD,
            vital=Vital(vital),
            priority=Priority.HIGH,
            value=value,
            timestamp=T0,
            risk_id="RISK-009",
        )
    ]


def test_medium_escalates_to_high_and_high_is_kept_until_normal():
    """TC-015 / REQ-015: MEDIUM escalates to HIGH on a critical value; HIGH is raised once and kept until normal."""
    engine = AlarmEngine()
    feed(engine, series("spo2", [90] * 5))
    assert engine.current_priority("P-001", Vital.SPO2) is Priority.MEDIUM

    assert [e.priority for e in engine.process(reading(5, spo2=84))] == [Priority.HIGH]
    assert engine.process(reading(6, spo2=83)) == []  # still critical, not re-raised
    assert engine.process(reading(7, spo2=89)) == []  # non-critical again, no downgrade
    assert engine.current_priority("P-001", Vital.SPO2) is Priority.HIGH

    assert engine.process(reading(8, spo2=96)) == []
    assert engine.current_priority("P-001", Vital.SPO2) is None


def test_blood_pressure_has_no_critical_bypass_in_v1():
    """TC-015 / REQ-015: a single extreme systolic value is non-critical only (no HIGH for BP in v1)."""
    engine = AlarmEngine()
    events = feed(engine, series("sys_bp", [60] * 5))
    assert events[:4] == [[], [], [], []]
    assert [e.priority for e in events[4]] == [Priority.MEDIUM]


# ---------------------------------------------------------------------------
# Boundary rule: equal to a limit is normal, strictly beyond is a violation
# ---------------------------------------------------------------------------

NON_CRITICAL_LIMITS = [
    ("spo2", 92, 91),
    ("hr", 50, 49),
    ("hr", 120, 121),
    ("sys_bp", 90, 89),
    ("sys_bp", 180, 181),
]


@pytest.mark.parametrize(("vital", "at_limit", "beyond"), NON_CRITICAL_LIMITS)
def test_non_critical_boundaries(vital, at_limit, beyond):
    """TC-015 / REQ-015: a value equal to a non-critical limit is normal, one step beyond is a violation."""
    engine = AlarmEngine()
    assert all(e == [] for e in feed(engine, series(vital, [at_limit] * 6)))

    events = feed(engine, series(vital, [beyond] * 5, start=6))
    assert [(e.vital, e.priority) for per in events for e in per] == [(Vital(vital), Priority.MEDIUM)]


CRITICAL_LIMITS = [("spo2", 85, 84), ("hr", 40, 39), ("hr", 150, 151)]


@pytest.mark.parametrize(("vital", "at_limit", "beyond"), CRITICAL_LIMITS)
def test_critical_boundaries(vital, at_limit, beyond):
    """TC-015 / REQ-015: a value equal to a critical limit is not critical, one step beyond gives HIGH."""
    engine = AlarmEngine()
    assert engine.process(reading(0, **{vital: at_limit})) == []

    events = engine.process(reading(1, **{vital: beyond}))
    assert [(e.vital, e.priority) for e in events] == [(Vital(vital), Priority.HIGH)]


# ---------------------------------------------------------------------------
# Per-patient thresholds
# ---------------------------------------------------------------------------

COPD_LIKE = Thresholds(spo2=VitalThresholds(non_critical=Limit(low=88), critical=Limit(low=80)))


def test_per_patient_override_changes_the_outcome():
    """TC-015 / REQ-015: a per-patient threshold override changes the alarm outcome for that patient only."""
    engine = AlarmEngine()
    engine.set_thresholds("P-002", COPD_LIKE)

    default_events = feed(engine, series("spo2", [90] * 5, patient_id="P-001"))
    override_events = feed(engine, series("spo2", [90] * 5, patient_id="P-002"))
    assert [e.priority for e in default_events[4]] == [Priority.MEDIUM]
    assert all(e == [] for e in override_events)

    # 84 % is critical by default but only non-critical under the override.
    assert [e.priority for e in engine.process(reading(5, "P-001", spo2=84))] == [Priority.HIGH]
    assert engine.process(reading(5, "P-002", spo2=84)) == []

    assert engine.thresholds_for("P-002") is COPD_LIKE
    assert engine.thresholds_for("P-999") == Thresholds()


def test_threshold_change_keeps_running_confirmation():
    """TC-015 / REQ-015: changing thresholds mid-episode does not restart the confirmation window."""
    engine = AlarmEngine()
    feed(engine, series("hr", [125] * 3))
    engine.set_thresholds("P-001", Thresholds(hr=VitalThresholds(non_critical=Limit(low=50, high=110))))

    events = feed(engine, series("hr", [125] * 2, start=3))
    assert [e.priority for e in events[1]] == [Priority.MEDIUM]


def test_custom_default_thresholds():
    """TC-015 / REQ-015: the engine-wide default thresholds can be replaced."""
    engine = AlarmEngine(default_thresholds=COPD_LIKE)
    assert all(e == [] for e in feed(engine, series("spo2", [90] * 5)))


# ---------------------------------------------------------------------------
# RCM-002b rate-of-change artefact check (RISK-002)
# ---------------------------------------------------------------------------


def test_sudden_hr_jump_is_flagged_and_not_counted():
    """TC-002 / REQ-002: (RCM-002b) a sudden HR jump is flagged as suspected artefact and not counted."""
    engine = AlarmEngine()
    events = feed(engine, series("hr", [75, 140, 140, 140, 140, 140, 140]))

    assert events[0] == []
    assert events[1] == [
        AlarmEvent(
            patient_id="P-001",
            kind=AlarmKind.ARTEFACT_SUSPECTED,
            vital=Vital.HR,
            priority=Priority.LOW,
            value=140,
            timestamp=T0 + timedelta(seconds=1),
            risk_id="RISK-002",
        )
    ]
    # The flagged reading is not counted: readings 3-6 are violations 1-4 ...
    assert events[2:6] == [[], [], [], []]
    # ... and the MEDIUM alarm comes with the 5th counted violation (1 s later than without RCM-002b).
    assert [e.priority for e in events[6]] == [Priority.MEDIUM]


def test_isolated_spike_raises_only_low_events():
    """TC-002 / REQ-002: (RCM-002b) a one-reading spike and its return are both flagged; no threshold alarm."""
    engine = AlarmEngine()
    events = feed(engine, series("hr", [75, 145, 75]))

    flat = [e for per in events for e in per]
    assert [(e.kind, e.priority) for e in flat] == [(AlarmKind.ARTEFACT_SUSPECTED, Priority.LOW)] * 2
    assert engine.current_priority("P-001", Vital.HR) is None


def test_artefact_does_not_reset_a_running_confirmation():
    """TC-002 / REQ-002: (RCM-002b) a suspected artefact neither counts nor resets the confirmation window."""
    engine = AlarmEngine()
    feed(engine, series("hr", [125] * 4))  # 4 counted violations
    assert [e.kind for e in engine.process(reading(4, hr=60))] == [AlarmKind.ARTEFACT_SUSPECTED]
    assert [e.kind for e in engine.process(reading(5, hr=125))] == [AlarmKind.ARTEFACT_SUSPECTED]

    assert [e.priority for e in engine.process(reading(6, hr=125))] == [Priority.MEDIUM]


def test_artefact_never_masks_a_critical_value():
    """TC-015 / REQ-015, REQ-002: a critical value alarms HIGH at once even when it is a suspected artefact."""
    engine = AlarmEngine()
    engine.process(reading(0, hr=75))
    events = engine.process(reading(1, hr=160))

    assert [(e.kind, e.priority, e.risk_id) for e in events] == [
        (AlarmKind.ARTEFACT_SUSPECTED, Priority.LOW, "RISK-002"),
        (AlarmKind.THRESHOLD, Priority.HIGH, "RISK-009"),
    ]


def test_spo2_drop_is_flagged_but_rise_is_not():
    """TC-002 / REQ-002: (RCM-002b) an SpO2 drop of more than 15 points in 1 s is flagged, a fast rise is not."""
    engine = AlarmEngine()
    engine.set_thresholds("P-001", COPD_LIKE)  # 81 % is then non-critical
    events = feed(engine, series("spo2", [97, 81, 97]))

    assert [(e.kind, e.vital) for e in events[1]] == [(AlarmKind.ARTEFACT_SUSPECTED, Vital.SPO2)]
    assert events[2] == []


def test_change_equal_to_the_limit_is_not_an_artefact():
    """TC-002 / REQ-002: (RCM-002b) a change equal to the limit (HR 60 bpm, SpO2 15 points) is not flagged."""
    engine = AlarmEngine()
    engine.set_thresholds("P-001", COPD_LIKE)
    events = feed(engine, [reading(0, hr=70, spo2=97), reading(1, hr=130, spo2=82), reading(2, hr=70, spo2=97)])

    assert all(e.kind is not AlarmKind.ARTEFACT_SUSPECTED for per in events for e in per)


@pytest.mark.parametrize("gap_seconds", [0, 3, 15])
def test_rate_check_needs_a_recent_previous_reading(gap_seconds):
    """TC-002 / REQ-002: (RCM-002b) no artefact check without a previous reading 0 < gap <= 2 s."""
    engine = AlarmEngine()
    engine.process(reading(0, hr=75))
    events = engine.process(reading(gap_seconds, hr=140))

    assert all(e.kind is not AlarmKind.ARTEFACT_SUSPECTED for e in events)


def test_custom_artefact_limits():
    """TC-002 / REQ-002: (RCM-002b) the rate-of-change limits are configurable."""
    engine = AlarmEngine(artefact_limits=ArtefactLimits(hr_max_change=20))
    events = feed(engine, series("hr", [75, 100]))
    assert [e.kind for e in events[1]] == [AlarmKind.ARTEFACT_SUSPECTED]


# ---------------------------------------------------------------------------
# REQ-003 data loss (RCM-001)
# ---------------------------------------------------------------------------


def test_data_loss_alarm_at_10_s_not_at_9_s_and_not_duplicated():
    """TC-003 / REQ-003: no DATA_LOSS at t + 9 s, exactly one at t + 10 s, repeated checks do not duplicate."""
    engine = AlarmEngine()
    engine.process(reading(0))

    assert engine.check_data_loss(T0 + timedelta(seconds=9)) == []
    assert engine.check_data_loss(T0 + timedelta(seconds=9, milliseconds=999)) == []
    assert engine.check_data_loss(T0 + timedelta(seconds=10)) == [
        AlarmEvent(
            patient_id="P-001",
            kind=AlarmKind.DATA_LOSS,
            vital=None,
            priority=Priority.HIGH,
            value=None,
            timestamp=T0 + timedelta(seconds=10),
            risk_id="RISK-001",
        )
    ]
    assert engine.check_data_loss(T0 + timedelta(seconds=11)) == []
    assert engine.check_data_loss(T0 + timedelta(seconds=60)) == []
    assert engine.data_loss_active("P-001")


def test_data_loss_is_raised_again_after_data_returned():
    """TC-003 / REQ-003: when data returns the alarm condition clears; a new silence raises a new alarm."""
    engine = AlarmEngine()
    engine.process(reading(0))
    assert len(engine.check_data_loss(T0 + timedelta(seconds=10))) == 1

    engine.process(reading(12))
    assert not engine.data_loss_active("P-001")
    assert engine.check_data_loss(T0 + timedelta(seconds=21)) == []
    assert len(engine.check_data_loss(T0 + timedelta(seconds=22))) == 1


def test_data_loss_is_tracked_per_patient():
    """TC-003 / REQ-003: only the silent patient gets a DATA_LOSS alarm."""
    engine = AlarmEngine()
    engine.process(reading(0, "P-001"))
    engine.process(reading(0, "P-002"))
    engine.process(reading(8, "P-002"))

    events = engine.check_data_loss(T0 + timedelta(seconds=10))
    assert [e.patient_id for e in events] == ["P-001"]
    assert not engine.data_loss_active("P-002")
    assert not engine.data_loss_active("P-unknown")


def test_no_data_loss_without_known_patients():
    """TC-003 / REQ-003: an engine that has seen no patient raises no DATA_LOSS alarm."""
    assert AlarmEngine().check_data_loss(T0) == []


def test_data_loss_check_rejects_naive_time():
    """TC-003 / REQ-003: check_data_loss rejects a naive (non-UTC-aware) time."""
    with pytest.raises(ValueError, match="timezone-aware"):
        AlarmEngine().check_data_loss(datetime(2026, 11, 10, 8, 0, 0))


def test_data_loss_timeout_is_configurable():
    """TC-003 / REQ-003: the data-loss timeout is a parameter (default 10 s)."""
    engine = AlarmEngine(data_loss_timeout=timedelta(seconds=3))
    engine.process(reading(0))
    assert len(engine.check_data_loss(T0 + timedelta(seconds=3))) == 1


# ---------------------------------------------------------------------------
# Model validation and contract
# ---------------------------------------------------------------------------


def test_reading_rejects_naive_timestamp():
    """TC-003 / REQ-003: readings must carry timezone-aware UTC timestamps (shared data contract)."""
    with pytest.raises(ValueError, match="timezone-aware"):
        VitalReading("P-001", "DEV-1", datetime(2026, 11, 10, 8, 0, 0), 75, 120, 80, 97)


@pytest.mark.parametrize(
    "build",
    [
        lambda: Limit(low=120, high=50),
        lambda: Limit(low=90, high=90),
        lambda: VitalThresholds(non_critical=Limit(low=92), critical=Limit(low=95)),
        lambda: VitalThresholds(non_critical=Limit(high=120), critical=Limit(high=110)),
    ],
)
def test_inconsistent_thresholds_are_rejected(build):
    """TC-015 / REQ-015: inconsistent thresholds (low >= high, critical inside non-critical) are rejected."""
    with pytest.raises(ValueError):
        build()


@pytest.mark.parametrize(
    "kwargs",
    [{"confirmation_readings": 0}, {"data_loss_timeout": timedelta(0)}],
)
def test_engine_rejects_invalid_parameters(kwargs):
    """TC-015 / REQ-015, REQ-003: a zero confirmation window or zero data-loss timeout is rejected."""
    with pytest.raises(ValueError):
        AlarmEngine(**kwargs)


def test_unknown_patient_has_no_active_alarm():
    """TC-015 / REQ-015: a patient the engine has not seen has no raised alarm."""
    assert AlarmEngine().current_priority("P-unknown", Vital.HR) is None


def test_events_serialize_with_contract_field_names():
    """TC-015 / REQ-015: alarm events serialize with the shared data-contract field names and values."""
    engine = AlarmEngine()
    engine.process(reading(0))
    high = engine.process(reading(1, spo2=82))[0].to_dict()
    loss = engine.check_data_loss(T0 + timedelta(seconds=11))[0].to_dict()

    assert high == {
        "patient_id": "P-001",
        "kind": "THRESHOLD",
        "vital": "spo2",
        "priority": "HIGH",
        "value": 82,
        "timestamp": "2026-11-10T08:00:01+00:00",
        "risk_id": "RISK-009",
    }
    assert loss["kind"] == "DATA_LOSS" and loss["vital"] is None and loss["value"] is None

"""Tests of the Device Simulator v1 (ARC-001, REQ-001).

``generate_reading`` is tested without a server; ``run`` is tested with a fake
clock against a mock transport and against the real API (FastAPI TestClient).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import importlib.util  # noqa: E402
import json  # noqa: E402
import statistics  # noqa: E402
from collections import Counter  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings, decode_key, generate_key  # noqa: E402
from app.ingestion.validation import check_plausibility  # noqa: E402
from app.main import create_app  # noqa: E402
from app.storage.repository import Repository  # noqa: E402

# Load simulator/simulator.py by path: the folder and the module share the name "simulator".
_spec = importlib.util.spec_from_file_location("meditrace_simulator", ROOT / "simulator" / "simulator.py")
sim = importlib.util.module_from_spec(_spec)
sys.modules["meditrace_simulator"] = sim
_spec.loader.exec_module(sim)

START = datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)
CONTRACT_FIELDS = {"device_id", "timestamp", "hr", "sys_bp", "dia_bp", "spo2"}


def series(scenario: str, patients: int = 3, seconds: int = 120, **kwargs) -> dict[str, list]:
    """Readings per device for ``seconds`` seconds (``None`` entries removed)."""
    states = sim.build_states(patients, scenario, start=START, **kwargs)
    return {
        s.device_id: [r for t in range(seconds) if (r := sim.generate_reading(s, scenario, t))]
        for s in states
    }


class FakeClock:
    """Monotonic clock whose sleep() advances time instantly."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept += seconds
        self.now += seconds


# --- generate_reading (pure function) --------------------------------------------


@pytest.mark.parametrize("scenario", sim.SCENARIOS)
def test_readings_follow_the_data_contract(scenario):
    """TC-001 / REQ-001: every reading has the contract fields, UTC ISO time, 1 s spacing."""
    for readings in series(scenario, seconds=40).values():
        assert readings, "every device sends at least one reading"
        previous = None
        for r in readings:
            assert set(r) == CONTRACT_FIELDS
            assert all(isinstance(r[v], int) for v in sim.VITALS)
            assert r["timestamp"].endswith("Z")
            ts = datetime.fromisoformat(r["timestamp"])
            assert ts.utcoffset() == timedelta(0)
            if previous is not None:
                assert ts - previous == timedelta(seconds=1)
            previous = ts


def test_normal_scenario_stays_inside_non_critical_limits():
    """TC-001 / REQ-001: 'normal' stays inside plausible ranges and the non-critical alarm limits."""
    for readings in series("normal", patients=5, seconds=600).values():
        for r in readings:
            assert check_plausibility(r).valid
            assert 50 <= r["hr"] <= 120
            assert r["spo2"] >= 92
            assert 90 <= r["sys_bp"] <= 180
            assert r["sys_bp"] > r["dia_bp"]
        # realistic baselines: HR 60-100, SpO2 95-99, BP about 120/80
        assert 60 <= statistics.mean(r["hr"] for r in readings) <= 100
        assert 95 <= statistics.mean(r["spo2"] for r in readings) <= 99
        assert 110 <= statistics.mean(r["sys_bp"] for r in readings) <= 130
        assert 70 <= statistics.mean(r["dia_bp"] for r in readings) <= 90


def test_artefact_scenario_produces_out_of_range_spikes():
    """TC-001 / REQ-001: 'artefact' produces implausible spikes and sudden plausible jumps."""
    readings = [r for rs in series("artefact", patients=3, seconds=300).values() for r in rs]
    invalid = [r for r in readings if not check_plausibility(r).valid]
    assert len(invalid) >= 5
    assert len(invalid) < 0.2 * len(readings)  # most readings stay normal
    assert any(r["hr"] > 120 and check_plausibility(r).valid for r in readings)  # plausible jump


def test_deterioration_scenario_trends_down():
    """TC-001 / REQ-001: 'deterioration' SpO2 falls below 92 and then below 85; HR never critical."""
    for readings in series("deterioration", patients=5, seconds=1200).values():
        spo2 = [r["spo2"] for r in readings]
        assert min(spo2[:10]) >= 94  # starts normal
        assert spo2[70] < 92  # non-critical violation after about a minute
        assert spo2[150] < 85  # critical value later
        windows = [sum(spo2[i : i + 20]) / 20 for i in range(0, 160, 20)]
        assert all(later <= earlier for earlier, later in zip(windows, windows[1:], strict=False))
        assert all(check_plausibility(r).valid for r in readings)  # real deterioration
        # only the SpO2 alarms are exercised: HR stays below the critical 150 bpm (20 min)
        assert max(r["hr"] for r in readings) < 150


def test_disconnect_scenario_stops_one_device():
    """TC-001 / REQ-001: 'disconnect' - device 1 goes silent after 15 s, the others continue."""
    states = sim.build_states(3, "disconnect", start=START, disconnect_after=15)
    first, *others = states
    assert all(sim.generate_reading(first, "disconnect", t) for t in range(15))
    assert all(sim.generate_reading(first, "disconnect", t) is None for t in range(15, 60))
    assert all(sim.generate_reading(s, "disconnect", t) for s in others for t in range(60))


def test_unpaired_scenario_adds_unknown_device():
    """TC-001 / REQ-001: 'unpaired' adds one device that is never paired."""
    states = sim.build_states(2, "unpaired", start=START)
    unpaired = [s for s in states if not s.paired]
    assert len(states) == 3 and len(unpaired) == 1
    assert unpaired[0].device_id not in {s.device_id for s in states if s.paired}
    assert sim.generate_reading(unpaired[0], "unpaired", 0)["device_id"] == unpaired[0].device_id


def test_boundary_scenario_covers_limits():
    """TC-001 / REQ-001: 'boundary' sends values exactly on and just outside the REQ-002 limits."""
    (readings,) = series("boundary", patients=1, seconds=len(sim.BOUNDARY_CASES)).values()
    hrs = {r["hr"] for r in readings}
    assert {20, 300, 19, 301} <= hrs
    validity = Counter(check_plausibility(r).valid for r in readings)
    assert validity[True] > 0 and validity[False] > 0


def test_generate_reading_is_deterministic_and_checks_input():
    """TC-001 / REQ-001: same state, scenario and second give the same reading; bad input rejected."""
    (state,) = sim.build_states(1, "artefact", start=START, seed=7)
    assert sim.generate_reading(state, "artefact", 42) == sim.generate_reading(state, "artefact", 42)
    with pytest.raises(ValueError):
        sim.generate_reading(state, "earthquake", 0)
    with pytest.raises(ValueError):
        sim.generate_reading(state, "normal", -1)
    with pytest.raises(ValueError):
        sim.build_states(0, "normal")


# --- run(): one reading per patient per second ------------------------------------


def test_run_sends_one_reading_per_patient_per_second():
    """TC-001 / REQ-001: 3 patients for 10 s -> 10 readings each, 1 s apart, after pairing."""
    requests: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append((request.url.path, body))
        if request.url.path == "/devices/pair":
            return httpx.Response(201, json={**body, "status": "paired"})
        return httpx.Response(201, json={"status": "accepted"})

    clock = FakeClock()
    states = sim.build_states(3, "normal", start=START)
    with httpx.Client(base_url="http://sim.test", transport=httpx.MockTransport(handler)) as client:
        summary = sim.run(
            client, states, "normal", duration=10, sleep=clock.sleep, clock=clock, log=lambda _m: None
        )

    pairs = [b for path, b in requests if path == "/devices/pair"]
    posts = [b for path, b in requests if path == "/readings"]
    assert len(pairs) == 3
    assert requests[:3] == [("/devices/pair", b) for b in pairs]  # pairing happens first
    per_device = Counter(b["device_id"] for b in posts)
    assert per_device == {s.device_id: 10 for s in states}
    assert summary.sent == 30 and summary.outcomes == {"accepted": 30}
    assert clock.slept == pytest.approx(9.0)  # ticks at t = 0..9 s


def test_run_against_real_api(tmp_path):
    """TC-001 / REQ-001, REQ-013: simulator -> API: paired readings stored, unpaired device rejected."""
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'sim.db'}",
        data_key=decode_key("DATA_KEY", generate_key()),
        index_key=decode_key("INDEX_KEY", generate_key()),
    )
    app = create_app(settings)
    clock = FakeClock()
    states = sim.build_states(2, "unpaired", start=START)
    with TestClient(app) as client:
        summary = sim.run(
            client, states, "unpaired", duration=5, sleep=clock.sleep, clock=clock, log=lambda _m: None
        )
        session = app.state.database.session()
        repo = Repository(session, app.state.cipher, settings.index_key)
        stored = {s.patient_id: repo.list_readings(s.patient_id, 100) for s in states if s.paired}
        events = repo.list_hazard_events()
        session.close()
    app.state.database.dispose()

    assert summary.outcomes == {"accepted": 10, "rejected": 5}
    assert all(len(readings) == 5 for readings in stored.values())
    assert [e.event_type for e in events] == ["UNPAIRED_DEVICE"] * 5
    assert {e.device_id for e in events} == {"SIM-DEV-UNPAIRED"}

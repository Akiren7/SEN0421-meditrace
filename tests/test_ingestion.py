"""Integration tests of Ingestion & Validation (ARC-002) through the HTTP API.

FastAPI TestClient + SQLite (``tmp_path``); same code path as PostgreSQL.
Integrity level 3 (IEEE 1012): REQ-002 and REQ-013 boundaries are covered
both through the API and at unit level.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from contextlib import contextmanager  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings, decode_key, generate_key  # noqa: E402
from app.hazard.log import EVENT_RISK, HazardEventType, HazardLog  # noqa: E402
from app.ingestion.validation import check_plausibility  # noqa: E402
from app.main import create_app  # noqa: E402
from app.storage.repository import Repository  # noqa: E402

T0 = datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)
NORMAL = {"hr": 72, "sys_bp": 120, "dia_bp": 80, "spo2": 97}


@pytest.fixture
def forwarded() -> list:
    """Readings handed to the Alarm Engine hook (the Sprint 3 wiring point)."""
    return []


@pytest.fixture
def app(tmp_path: Path, forwarded: list):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'ingestion.db'}",
        data_key=decode_key("DATA_KEY", generate_key()),
        index_key=decode_key("INDEX_KEY", generate_key()),
    )
    app = create_app(settings, alarm_sink=forwarded.append)
    yield app
    app.state.database.dispose()  # release the SQLite file (Windows keeps it locked)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@contextmanager
def repository(app):
    session = app.state.database.session()
    try:
        yield Repository(session, app.state.cipher, app.state.settings.index_key)
    finally:
        session.close()


def hazard_events(app) -> list:
    with repository(app) as repo:
        return repo.list_hazard_events()


def reading_count(app) -> int:
    with repository(app) as repo:
        return repo.count_readings()


def pair(client, device_id="D1", patient_id="P1", name="Test Patient"):
    return client.post(
        "/devices/pair",
        json={"device_id": device_id, "patient_id": patient_id, "patient_name": name},
    )


def reading(device_id="D1", timestamp=T0, **values) -> dict:
    ts = timestamp if isinstance(timestamp, str) else timestamp.isoformat()
    return {"device_id": device_id, "timestamp": ts, **NORMAL, **values}


# --- TC-013: device-patient pairing ----------------------------------------------


def test_pair_then_post_is_accepted(client, forwarded):
    """TC-013 / REQ-013: a paired device's reading is accepted and stored for its patient."""
    response = pair(client)
    assert response.status_code == 201
    assert response.json() == {"device_id": "D1", "patient_id": "P1", "status": "paired"}

    response = client.post("/readings", json=reading())
    assert response.status_code == 201
    assert response.json() == {"status": "accepted"}

    (stored,) = client.get("/patients/P1/readings").json()
    assert stored["patient_id"] == "P1" and stored["device_id"] == "D1"
    assert [r.patient_id for r in forwarded] == ["P1"]


def test_unknown_device_is_rejected_with_hazard_event(client, app, forwarded):
    """TC-013 / REQ-013: unpaired device -> 422, not stored, not forwarded, UNPAIRED_DEVICE event."""
    pair(client)
    response = client.post("/readings", json=reading(device_id="D9"))
    assert response.status_code == 422
    assert "not paired" in response.json()["detail"]

    assert reading_count(app) == 0
    assert forwarded == []
    (event,) = hazard_events(app)
    assert event.event_type == "UNPAIRED_DEVICE"
    assert event.device_id == "D9" and event.patient_id is None
    assert event.risk_id == "RISK-008"


def test_repairing_device_to_other_patient_conflicts(client, app):
    """TC-013 / REQ-013: re-pairing D1 to another patient -> 409; existing pairing unchanged."""
    pair(client, "D1", "P1")
    response = pair(client, "D1", "P2", "Second Patient")
    assert response.status_code == 409

    client.post("/readings", json=reading())
    (stored,) = client.get("/patients/P1/readings").json()
    assert stored["patient_id"] == "P1"
    assert client.get("/patients/P2/readings").status_code == 404  # P2 was not created
    with repository(app) as repo:
        assert repo.get_device_patient("D1") == "P1"


def test_same_pairing_again_is_idempotent(client):
    """TC-013 / REQ-013: pairing the same device with the same patient again -> 200, no change."""
    assert pair(client).status_code == 201
    response = pair(client)
    assert response.status_code == 200
    assert response.json()["status"] == "already_paired"


def test_second_device_for_same_patient_conflicts(client):
    """TC-013 / REQ-013: a patient cannot get a second device (1:1 pairing, RCM-008)."""
    pair(client, "D1", "P1")
    assert pair(client, "D2", "P1").status_code == 409


def test_patient_id_with_different_name_conflicts(client):
    """TC-013 / REQ-013: an existing patient ID with a different name -> 409 (wrong-patient guard)."""
    pair(client, "D1", "P1", "Test Patient")
    assert pair(client, "D1", "P1", "Another Person").status_code == 409


# --- TC-002: plausibility check -------------------------------------------------


def test_hr_350_is_invalid_with_hazard_event(client, app, forwarded):
    """TC-002 / REQ-002: HR 350 -> stored invalid, IMPLAUSIBLE_VALUE event, not forwarded."""
    pair(client)
    response = client.post("/readings", json=reading(hr=350))
    assert response.status_code == 201
    assert response.json() == {"status": "invalid"}

    (stored,) = client.get("/patients/P1/readings").json()
    assert stored["valid"] is False and stored["hr"] == 350
    assert forwarded == []  # invalid readings never reach the Alarm Engine

    (event,) = hazard_events(app)
    assert event.event_type == "IMPLAUSIBLE_VALUE"
    assert event.risk_id == "RISK-002"
    assert (event.patient_id, event.device_id) == ("P1", "D1")
    assert "hr" in event.detail
    assert "350" not in event.detail  # vital values stay encrypted (REQ-010)


def test_boundary_hr_20_and_300_are_accepted(client, app, forwarded):
    """TC-002 / REQ-002: boundary values HR 20 and HR 300 are plausible and accepted."""
    pair(client)
    for second, hr in enumerate((20, 300)):
        response = client.post("/readings", json=reading(timestamp=T0 + timedelta(seconds=second), hr=hr))
        assert response.json() == {"status": "accepted"}
    assert [r.hr for r in forwarded] == [20, 300]
    assert hazard_events(app) == []


def test_several_violations_give_one_hazard_event(client, app):
    """TC-002 / REQ-002: one implausible reading -> exactly one hazard event listing all rules."""
    pair(client)
    client.post("/readings", json=reading(hr=10, spo2=120, sys_bp=70, dia_bp=90))
    (event,) = hazard_events(app)
    for part in ("hr", "spo2", "sys_bp not greater than dia_bp"):
        assert part in event.detail


@pytest.mark.parametrize(
    ("values", "valid"),
    [
        ({"hr": 20}, True),
        ({"hr": 300}, True),
        ({"hr": 19}, False),
        ({"hr": 301}, False),
        ({"spo2": 50}, True),
        ({"spo2": 100}, True),
        ({"spo2": 49}, False),
        ({"spo2": 101}, False),
        ({"sys_bp": 40, "dia_bp": 20}, True),
        ({"sys_bp": 300, "dia_bp": 200}, True),
        ({"sys_bp": 39, "dia_bp": 20}, False),
        ({"sys_bp": 301, "dia_bp": 80}, False),
        ({"dia_bp": 19, "sys_bp": 120}, False),
        ({"dia_bp": 201, "sys_bp": 250}, False),
        ({"sys_bp": 120, "dia_bp": 120}, False),
        ({"sys_bp": 121, "dia_bp": 120}, True),
    ],
)
def test_plausibility_limits_are_inclusive(values, valid):
    """TC-002 / REQ-002: inclusive limits and systolic > diastolic (SRS acceptance criteria 2-3)."""
    result = check_plausibility({**NORMAL, **values})
    assert result.valid is valid
    assert bool(result.reasons) is not valid


# --- TC-001: storage and retrieval of readings ----------------------------------


def test_valid_reading_stored_and_returned_newest_first(client):
    """TC-001 / REQ-001: valid readings are stored and returned decrypted, newest first."""
    pair(client)
    for offset, hr in ((1, 71), (0, 70), (2, 72)):  # posted out of order on purpose
        client.post("/readings", json=reading(timestamp=T0 + timedelta(seconds=offset), hr=hr))

    readings = client.get("/patients/P1/readings").json()
    assert [r["hr"] for r in readings] == [72, 71, 70]
    assert readings[0] == {
        "patient_id": "P1",
        "device_id": "D1",
        "timestamp": "2026-11-14T10:00:02Z",
        "hr": 72,
        "sys_bp": 120,
        "dia_bp": 80,
        "spo2": 97,
        "valid": True,
    }
    assert [r["hr"] for r in client.get("/patients/P1/readings?limit=2").json()] == [72, 71]


def test_timestamps_are_stored_in_utc(client):
    """TC-001 / REQ-001: a timestamp with a +03:00 offset is stored and returned in UTC."""
    pair(client)
    client.post("/readings", json=reading(timestamp="2026-11-14T13:00:05+03:00"))
    (stored,) = client.get("/patients/P1/readings").json()
    assert stored["timestamp"] == "2026-11-14T10:00:05Z"


def test_readings_query_validation(client):
    """TC-001 / REQ-001: unknown patient -> 404; limit outside 1..86400 -> 422."""
    pair(client)
    assert client.get("/patients/NOPE/readings").status_code == 404
    assert client.get("/patients/P1/readings?limit=0").status_code == 422
    assert client.get("/patients/P1/readings?limit=86401").status_code == 422


def test_tampered_reading_gives_clear_error_not_wrong_data(client, tmp_path):
    """TC-010 / REQ-010: tampered stored vitals -> GET answers 500 with a clear message, no data."""
    import sqlite3

    pair(client)
    client.post("/readings", json=reading())
    with sqlite3.connect(tmp_path / "ingestion.db") as conn:
        (blob,) = conn.execute("SELECT vitals_enc FROM readings").fetchone()
        conn.execute("UPDATE readings SET vitals_enc = ?", (blob[:-1] + bytes([blob[-1] ^ 1]),))
    response = client.get("/patients/P1/readings")
    assert response.status_code == 500
    assert response.json() == {
        "detail": "stored data could not be decrypted (wrong DATA_KEY or tampered data)"
    }


# --- TC-012: hazard log ---------------------------------------------------------


def test_every_hazard_event_has_required_fields(client, app):
    """TC-012 / REQ-012: each hazard event has UTC time, type, RISK ID and patient/device when known."""
    pair(client)
    before = datetime.now(UTC)
    client.post("/readings", json=reading(hr=350))  # IMPLAUSIBLE_VALUE, patient known
    client.post("/readings", json=reading(device_id="D9"))  # UNPAIRED_DEVICE, patient unknown
    after = datetime.now(UTC)

    events = hazard_events(app)
    assert [e.event_type for e in events] == ["IMPLAUSIBLE_VALUE", "UNPAIRED_DEVICE"]
    for event in events:
        assert event.id is not None
        assert event.timestamp.utcoffset() == timedelta(0)
        assert before - timedelta(seconds=1) <= event.timestamp <= after + timedelta(seconds=1)
        assert event.risk_id == EVENT_RISK[HazardEventType(event.event_type)]
        assert event.device_id is not None
        assert event.detail
    assert events[0].patient_id == "P1"
    assert events[1].patient_id is None


def test_hazard_log_maps_every_event_type_to_its_risk(app):
    """TC-012 / REQ-012: event type -> RISK ID mapping of the shared data contract."""
    expected = {
        "IMPLAUSIBLE_VALUE": "RISK-002",
        "UNPAIRED_DEVICE": "RISK-008",
        "DATA_LOSS": "RISK-001",
        "ARTEFACT_SUSPECTED": "RISK-002",
        "AUTH_FAILURE": "RISK-006",
    }
    app.state.database.create_all()
    with repository(app) as repo:
        log = HazardLog(repo)
        for event_type in HazardEventType:
            log.record(event_type, detail="test event", device_id="D1")
        repo.commit()
        stored = {e.event_type: e.risk_id for e in repo.list_hazard_events()}
    assert stored == expected
    with pytest.raises(ValueError):
        HazardLog(None).record("NOT_A_TYPE", detail="x")  # type: ignore[arg-type]


# --- Robustness smoke check ---------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"device_id": "D1", "timestamp": "2026-11-14T10:00:00Z", "hr": 72, "sys_bp": 120, "dia_bp": 80},
        {**reading(), "hr": "72"},
        {**reading(), "hr": 72.5},
        {**reading(), "hr": True},
        {**reading(), "timestamp": "2026-11-14T10:00:00"},  # no time zone
        {**reading(), "timestamp": "yesterday"},
        {**reading(), "patient_id": "P2"},  # unknown field
        {**reading(), "device_id": ""},
        {**reading(), "device_id": "D1; DROP TABLE readings"},
    ],
)
def test_malformed_requests_are_rejected_and_service_continues(client, app, body):
    """Robustness smoke check: malformed request -> 422, nothing stored, next valid reading accepted.

    Prepares TC-019 (REQ-019, 1-hour fault-injection run in R4). Deliberately not
    tagged TC-019 so that the compliance report does not show REQ-019 as
    verified by this short check (RCM-010).
    """
    pair(client)
    assert client.post("/readings", json=body).status_code == 422
    assert reading_count(app) == 0
    assert client.post("/readings", json=reading()).json() == {"status": "accepted"}


def test_invalid_json_body_is_rejected(client):
    """Robustness smoke check: a body that is not JSON -> 422, no server error."""
    response = client.post(
        "/readings", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert client.get("/health").json() == {"status": "ok"}

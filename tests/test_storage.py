"""Tests of the Encrypted Data Layer (ARC-007): AES-256-GCM, blind index, key settings.

Runs on SQLite through the same SQLAlchemy code that runs on PostgreSQL.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import sqlite3  # noqa: E402
import statistics  # noqa: E402
import time  # noqa: E402
from datetime import UTC, datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import inspect  # noqa: E402
from sqlalchemy.exc import StatementError  # noqa: E402

from app.config import ConfigError, Settings, decode_key, generate_key  # noqa: E402
from app.db import Database  # noqa: E402
from app.storage.crypto import (  # noqa: E402
    DecryptionError,
    FieldCipher,
    blind_index,
    normalize_name,
)
from app.storage.repository import Repository  # noqa: E402

T0 = datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)
VITALS = {"hr": 77, "sys_bp": 123, "dia_bp": 81, "spo2": 96}


class CountingCipher(FieldCipher):
    """FieldCipher that counts decryptions (to prove the blind index avoids them)."""

    def __init__(self, key: bytes) -> None:
        super().__init__(key)
        self.decryptions = 0

    def decrypt(self, blob: bytes, associated_data: bytes | None = None) -> bytes:
        self.decryptions += 1
        return super().decrypt(blob, associated_data)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "storage.db"


@pytest.fixture
def database(db_path: Path):
    database = Database(f"sqlite:///{db_path}")
    database.create_all()
    yield database
    database.dispose()


@pytest.fixture
def keys() -> tuple[bytes, bytes]:
    return decode_key("DATA_KEY", generate_key()), decode_key("INDEX_KEY", generate_key())


@pytest.fixture
def repo(database: Database, keys: tuple[bytes, bytes]):
    session = database.session()
    yield Repository(session, CountingCipher(keys[0]), keys[1])
    session.close()


def store_patient_and_reading(repo: Repository, name: str = "Test Patient") -> None:
    repo.pair_device("D1", "P1", name)
    repo.add_reading(patient_id="P1", device_id="D1", timestamp=T0, vitals=VITALS, valid=True)
    repo.commit()


# --- TC-010: encryption at rest -------------------------------------------------


def test_raw_database_contains_no_plaintext(repo: Repository, database: Database, db_path: Path):
    """TC-010 / REQ-010: raw DB has neither the patient name nor vital values in plaintext."""
    store_patient_and_reading(repo)
    database.dispose()  # make sure everything is on disk

    raw = db_path.read_bytes()
    assert b"Test Patient" not in raw
    assert "Test Patient".encode("utf-16-le") not in raw
    for name in VITALS:  # the JSON field names would be visible if the blob were plaintext
        assert f'"{name}"'.encode() not in raw

    columns = {c["name"] for c in inspect(database.engine).get_columns("readings")}
    assert not columns & set(VITALS), "vital values must not have clear-text columns"

    with sqlite3.connect(db_path) as conn:
        name_enc, name_index = conn.execute("SELECT name_enc, name_index FROM patients").fetchone()
        (vitals_enc,) = conn.execute("SELECT vitals_enc FROM readings").fetchone()
    assert b"Test" not in name_enc
    assert len(name_index) == 64 and "test" not in name_index.lower()
    assert len(vitals_enc) > 12 + 16  # nonce || ciphertext || tag


def test_decrypt_round_trip(repo: Repository):
    """TC-010 / REQ-010: reading through ARC-007 returns the original name and values."""
    store_patient_and_reading(repo)
    patient = repo.get_patient("P1")
    assert patient is not None and patient.name == "Test Patient"
    (reading,) = repo.list_readings("P1", limit=10)
    assert {k: getattr(reading, k) for k in VITALS} == VITALS
    assert reading.timestamp == T0 and reading.timestamp.tzinfo is not None
    assert reading.valid is True


def test_tampered_ciphertext_raises(repo: Repository, db_path: Path):
    """TC-010 / REQ-010: a modified ciphertext byte raises a decryption error, not wrong data."""
    store_patient_and_reading(repo)
    with sqlite3.connect(db_path) as conn:
        (blob,) = conn.execute("SELECT vitals_enc FROM readings").fetchone()
        tampered = bytearray(blob)
        tampered[20] ^= 0x01
        conn.execute("UPDATE readings SET vitals_enc = ?", (bytes(tampered),))
        (name_blob,) = conn.execute("SELECT name_enc FROM patients").fetchone()
        conn.execute("UPDATE patients SET name_enc = ?", (name_blob[:-1] + bytes([name_blob[-1] ^ 1]),))
    repo._session.expire_all()  # forget cached rows, read the tampered ones
    with pytest.raises(DecryptionError):
        repo.list_readings("P1", limit=10)
    with pytest.raises(DecryptionError):
        repo.get_patient("P1")


def test_ciphertext_moved_to_other_patient_raises(repo: Repository, db_path: Path):
    """TC-010 / REQ-010: an encrypted name copied to another patient's row does not decrypt (AAD)."""
    repo.pair_device("D1", "P1", "Test Patient")
    repo.pair_device("D2", "P2", "Other Patient")
    repo.commit()
    with sqlite3.connect(db_path) as conn:
        (blob,) = conn.execute("SELECT name_enc FROM patients WHERE id = 'P1'").fetchone()
        conn.execute("UPDATE patients SET name_enc = ? WHERE id = 'P2'", (blob,))
    repo._session.expire_all()
    assert repo.get_patient("P1").name == "Test Patient"
    with pytest.raises(DecryptionError):
        repo.get_patient("P2")


def test_wrong_key_cannot_decrypt(keys: tuple[bytes, bytes]):
    """TC-010 / REQ-010: data encrypted with one DATA_KEY cannot be read with another key."""
    blob = FieldCipher(keys[0]).encrypt_json(VITALS, b"aad")
    other = FieldCipher(decode_key("DATA_KEY", generate_key()))
    with pytest.raises(DecryptionError):
        other.decrypt_json(blob, b"aad")
    assert FieldCipher(keys[0]).decrypt_json(blob, b"aad") == VITALS


def test_cipher_uses_fresh_nonce_and_checks_input(keys: tuple[bytes, bytes]):
    """TC-010 / REQ-010: random 96-bit nonce per value; short blobs and bad keys are rejected."""
    cipher = FieldCipher(keys[0])
    first, second = cipher.encrypt(b"same value"), cipher.encrypt(b"same value")
    assert first != second and first[:12] != second[:12]
    with pytest.raises(DecryptionError):
        cipher.decrypt(b"too short")
    with pytest.raises(ValueError):
        FieldCipher(b"16-byte-key-1234")


# --- TC-010: blind index (PLN-05, closes RSK-06) ---------------------------------


def test_blind_index_finds_exact_name_not_partial(repo: Repository):
    """TC-010 / REQ-010: the blind index finds the exact name, not a partial name."""
    store_patient_and_reading(repo)
    repo.pair_device("D2", "P2", "Test Patient Junior")
    repo.commit()

    assert [p.id for p in repo.find_patient_by_name("Test Patient")] == ["P1"]
    assert [p.id for p in repo.find_patient_by_name("  test   PATIENT ")] == ["P1"]
    assert repo.find_patient_by_name("Test") == []
    assert repo.find_patient_by_name("Test Patien") == []
    assert repo.find_patient_by_name("Unknown Person") == []


def test_blind_index_search_does_not_decrypt_all_rows(repo: Repository):
    """TC-010 / REQ-010: name search decrypts only matching rows (no decrypt-all)."""
    for i in range(30):
        repo.pair_device(f"D{i}", f"P{i}", f"Simulated Patient {i}")
    repo.commit()
    cipher = repo._cipher
    cipher.decryptions = 0
    result = repo.find_patient_by_name("Simulated Patient 17")
    assert [p.id for p in result] == ["P17"]
    assert cipher.decryptions == 1


def test_blind_index_handles_turkish_dotted_and_dotless_i(repo: Repository):
    """TC-010 / REQ-010: 'AYŞE YILMAZ' and 'Ayşe Yılmaz' give the same blind index."""
    repo.pair_device("D1", "P1", "Ayşe Yılmaz")
    repo.pair_device("D2", "P2", "İsmail Işık")
    repo.commit()
    assert [p.id for p in repo.find_patient_by_name("AYŞE YILMAZ")] == ["P1"]
    assert [p.id for p in repo.find_patient_by_name("ismail ışık")] == ["P2"]
    assert [p.id for p in repo.find_patient_by_name("ISMAIL IŞIK")] == ["P2"]
    assert repo.find_patient_by_name("Ayse Yilmaz") == []  # ş vs s: different name
    assert normalize_name("İSMAİL") == normalize_name("ismail") == "ismail"


def test_blind_index_depends_on_separate_key(keys: tuple[bytes, bytes]):
    """TC-010 / REQ-010: the index is an HMAC with INDEX_KEY (another key gives another index)."""
    other_key = decode_key("INDEX_KEY", generate_key())
    assert blind_index(keys[1], "Test Patient") == blind_index(keys[1], "test patient")
    assert blind_index(keys[1], "Test Patient") != blind_index(other_key, "Test Patient")
    with pytest.raises(ValueError):
        blind_index(b"short", "Test Patient")


# --- TC-010: key configuration (no keys in the repository) ----------------------


def test_settings_validate_keys():
    """TC-010 / REQ-010: keys come from the environment, must be 32 bytes and different."""
    data_key, index_key = generate_key(), generate_key()
    settings = Settings.from_env({"DATA_KEY": data_key, "INDEX_KEY": index_key})
    assert settings.database_url == "sqlite:///./meditrace.db"
    assert not settings.ephemeral_keys
    assert data_key not in repr(settings) and "<hidden>" in repr(settings)

    with pytest.raises(ConfigError):
        Settings.from_env({"DATA_KEY": data_key})  # INDEX_KEY missing
    with pytest.raises(ConfigError):
        Settings.from_env({"DATA_KEY": data_key, "INDEX_KEY": data_key})  # same key
    with pytest.raises(ConfigError):
        Settings.from_env({"DATA_KEY": "c2hvcnQ=", "INDEX_KEY": index_key})  # 5 bytes
    with pytest.raises(ConfigError):
        Settings.from_env({"DATA_KEY": "not base64!", "INDEX_KEY": index_key})


def test_settings_without_keys_use_ephemeral_keys(caplog: pytest.LogCaptureFixture):
    """TC-010 / REQ-010: without keys: random per-run keys, in-memory database only, warning."""
    with caplog.at_level("WARNING", logger="meditrace.config"):
        first = Settings.from_env({})
    second = Settings.from_env({"DATABASE_URL": "sqlite:///:memory:"})
    assert first.ephemeral_keys and first.database_url == "sqlite://"
    assert second.ephemeral_keys and second.database_url == "sqlite:///:memory:"
    assert first.data_key != second.data_key
    assert "DATA_KEY and INDEX_KEY are not set" in caplog.text


@pytest.mark.parametrize(
    "url", ["sqlite:///./meditrace.db", "postgresql+psycopg://u:p@db:5432/meditrace"]
)
def test_persistent_database_requires_keys(url):
    """TC-010 / REQ-010: random keys are never combined with a persistent database.

    Otherwise rows written before a restart (every code change with --reload)
    could not be decrypted any more and re-pairing would fail with 409.
    """
    with pytest.raises(ConfigError, match="required for a persistent DATABASE_URL"):
        Settings.from_env({"DATABASE_URL": url})


def test_development_mode_api_works_without_keys():
    """TC-010 / REQ-010: without keys the API runs on an in-memory database shared by all requests."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(Settings.from_env({}))
    with TestClient(app) as client:
        pair = {"device_id": "D1", "patient_id": "P1", "patient_name": "Test Patient"}
        assert client.post("/devices/pair", json=pair).status_code == 201
        reading = {"device_id": "D1", "timestamp": "2026-11-14T10:00:00Z", **VITALS}
        assert client.post("/readings", json=reading).json() == {"status": "accepted"}
        assert [r["hr"] for r in client.get("/patients/P1/readings").json()] == [77]


# --- TC-020: encryption overhead (smoke benchmark) ------------------------------


def _p95(samples: list[float]) -> float:
    return statistics.quantiles(samples, n=100)[94]


def test_encryption_overhead_p95(keys: tuple[bytes, bytes], record_testsuite_property):
    """TC-020 / REQ-020: (smoke) encrypt and decrypt of 10 000 readings, p95 <= 20 ms each.

    The only difference between an encrypted and a plaintext read/write is the
    crypto step, so its duration is the overhead. The full benchmark through the
    database on the CI runner follows in R4.
    """
    cipher = FieldCipher(keys[0])
    aad = b"readings.vitals|P1|D1"
    encrypt_ms, decrypt_ms = [], []
    for i in range(10_000):
        payload = {**VITALS, "hr": 60 + i % 40}
        start = time.perf_counter()
        blob = cipher.encrypt_json(payload, aad)
        middle = time.perf_counter()
        assert cipher.decrypt_json(blob, aad) == payload
        end = time.perf_counter()
        encrypt_ms.append((middle - start) * 1000)
        decrypt_ms.append((end - middle) * 1000)

    p95_encrypt, p95_decrypt = _p95(encrypt_ms), _p95(decrypt_ms)
    # Test-suite properties are kept in the JUnit XML (xunit2) read by the Compliance Reporter.
    record_testsuite_property("TC-020_encrypt_p95_ms", round(p95_encrypt, 4))
    record_testsuite_property("TC-020_decrypt_p95_ms", round(p95_decrypt, 4))
    print(f"\nTC-020 encryption p95 = {p95_encrypt:.4f} ms, decryption p95 = {p95_decrypt:.4f} ms")
    assert p95_encrypt <= 20.0
    assert p95_decrypt <= 20.0


def test_utc_timestamps_survive_storage(repo: Repository):
    """TC-001 / REQ-001: timestamps are stored and returned in UTC; naive ones are refused (A6)."""
    repo.pair_device("D1", "P1", "Test Patient")
    istanbul = datetime(2026, 11, 14, 13, 0, 0, tzinfo=timezone(timedelta(hours=3)))
    repo.add_reading(patient_id="P1", device_id="D1", timestamp=istanbul, vitals=VITALS, valid=True)
    repo.commit()
    repo._session.expire_all()
    (reading,) = repo.list_readings("P1", limit=1)
    assert reading.timestamp == datetime(2026, 11, 14, 10, 0, 0, tzinfo=UTC)
    assert reading.timestamp.utcoffset() == timedelta(0)

    with pytest.raises(StatementError, match="naive datetime"):
        repo.add_reading(
            patient_id="P1", device_id="D1", timestamp=datetime(2026, 1, 1), vitals=VITALS, valid=True
        )

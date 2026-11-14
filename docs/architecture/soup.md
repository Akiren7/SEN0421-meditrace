# SOUP list — MediTrace

IEC 62304 §5.3.3 / §5.3.4 (SOUP functional and performance requirements, hardware/software needed) and §8.1.2 (identification of SOUP). Software safety class B.

- **Pinned in:** `backend/requirements.txt` (exact `==` versions, installed and tested with Python 3.12 on 14.11.2026, PLN-08).
- **Change rule:** a SOUP version changes only through a pull request that updates this table and `backend/requirements.txt`, with all tests green in CI.
- **Anomaly lists:** before each release (R4) the team checks the published issues / security advisories of every package below and records the result here.

## Direct SOUP (pinned)

| # | Name | Version | Purpose in MediTrace | Required function (what we rely on) | Known risk → mitigation / verification |
| - | ---- | ------- | -------------------- | ----------------------------------- | -------------------------------------- |
| 1 | fastapi | 0.162.7 | HTTP API of the backend (ARC-002 now, ARC-005/006 in Sprint 3) | Routes requests to the right endpoint; rejects bodies that do not match the Pydantic schema with HTTP 422 | Malformed input could reach business logic → strict schemas (`extra="forbid"`, `StrictInt`, aware timestamps); robustness tests in `tests/test_ingestion.py`; full fault injection TC-019 in R4 |
| 2 | uvicorn | 0.54.0 | ASGI server that runs the API | Serves HTTP on port 8000; keeps running under load | Server crash/hang stops data flow (RISK-001) → data-loss alarm REQ-003 does not depend on a request arriving; Docker health check on `/health`; soak test TC-024 in R4 |
| 3 | pydantic | 2.14.3 | Request/response models (`app/schemas.py`) | Type validation, time-zone-aware timestamps, UTC serialisation | Lax type coercion (`"72"` → 72, `true` → 1) could hide device faults → `StrictInt` for vitals; covered by parametrized malformed-input tests |
| 4 | sqlalchemy | 2.1.8 | ORM / database access, only inside ARC-007 (`app/storage/repository.py`) | Parameterised SQL (no SQL injection), transactions, same code on SQLite and PostgreSQL | Unit of work does **not** order INSERTs by foreign key when no `relationship()` is defined (found in Sprint 2, see notes) → explicit flush of the patient before the device; SQLite `foreign_keys=ON` so tests catch FK errors; TC-013 |
| 5 | psycopg[binary] | 3.3.9 | PostgreSQL 16 driver (Docker Compose) | Connects SQLAlchemy to PostgreSQL | Not exercised in CI (tests use SQLite) → manual `docker compose up` + simulator smoke test; CI job with a PostgreSQL service planned with Mert (Sprint 3/4). The binary wheel bundles libpq/OpenSSL → pinned version |
| 6 | cryptography | 50.0.2 | AES-256-GCM field encryption (`app/storage/crypto.py`) | Encrypts with a 256-bit key; **must reject tampered ciphertext** (GCM tag) | Tampered data returned as wrong values / nonce reuse → random 96-bit nonce per value, associated data per row; covered by TC-010 (tamper, wrong key, moved ciphertext, fresh nonce) and TC-020 (p95 overhead) |
| 7 | argon2-cffi | 25.1.0 | Password hashing for login (ARC-005, REQ-008) — **used from Sprint 3** | Argon2id hash and verify | Weak parameters → use library defaults (Argon2id) and test lockout TC-008 in Sprint 3 |
| 8 | pytest | 9.2.0 | Test runner (unit, integration), JUnit output for the Compliance Reporter | Runs all `tests/test_*.py`, reports failures, writes JUnit XML | False "pass" → tests tagged `TC-xxx / REQ-xxx`; reporter shows OK only with a real passing result (RCM-010) |
| 9 | httpx | 0.28.1 | HTTP client of the Device Simulator (`simulator/simulator.py`); `MockTransport` in simulator tests | Sends JSON POST requests with a timeout | Network errors stop the simulator → caught and counted, run continues (TC-001 tests) |
| 10 | httpx2 | 2.16.0 | Transport of FastAPI/Starlette `TestClient` (tests only) | In-process HTTP calls to the app in tests | Starlette 1.10 deprecates `httpx` for `TestClient` (`StarletteDeprecationWarning`, reported by Barış in Sprint 2) → `httpx2` installed so `TestClient` uses it and the warning is gone |

## Platform SOUP

| Name | Version | Purpose | Known risk → mitigation |
| ---- | ------- | ------- | ----------------------- |
| CPython | 3.12 (CI: `actions/setup-python` 3.12; local 3.12.5) | Runtime of backend, simulator, tests | Version drift between laptops (3.14 found on one laptop) → everyone uses a 3.12 venv |
| PostgreSQL | `postgres:16` Docker image | Production-like database | Floating minor tag → pin image digest before release v1.0 (R4) |
| Python image | `python:3.12-slim` Docker image | Runs the API container | Floating tag → pin digest before release v1.0 (R4) |

## Indirect SOUP (installed as dependencies, recorded for reproducibility)

Resolved by pip on 14.11.2026 together with the pins above (not pinned directly; any change shows up in `pip freeze` and is reviewed in the PR):

starlette 1.10.0 (HTTP toolkit under FastAPI) · pydantic_core 2.50.4 · annotated-types 0.8.0 · annotated-doc 0.0.6 · typing_extensions 4.16.0 · typing-inspection 0.4.5 · anyio 4.16.0 · h11 0.16.0 · httpcore 1.0.9 · httpcore2 2.16.0 · truststore 0.10.5 · idna 3.20 · certifi 2026.10.23 · click 8.5.1 · colorama 0.4.6 · opentelemetry-api 1.45.2 (required by FastAPI) · psycopg-binary 3.3.9 · cffi 2.1.1 · pycparser 3.12 · argon2-cffi-bindings 26.2.0 · iniconfig 2.3.1 · pluggy 1.7.0 · packaging 26.3 · Pygments 2.21.0 · tzdata 2026.6.

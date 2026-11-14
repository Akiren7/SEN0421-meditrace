# Database schema v1 (Sprint 2, PLN-04)

Owner: ARC-007 Encrypted Data Layer — the **only** component that writes to the database (design decision 2). Defined in `backend/app/models.py`; tables are created on start-up (`create_all`). PostgreSQL 16 in Docker Compose, SQLite for local development and tests (same SQLAlchemy code).

Legend: 🔒 = AES-256-GCM ciphertext (`nonce 12 B || ciphertext || tag 16 B`, REQ-010). All timestamps are stored and returned in **UTC**; naive timestamps are rejected.

## `patients`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | varchar(64) PK | Ward patient number (pseudonymous, e.g. `SIM-P001`) — in clear for queries |
| `name_enc` 🔒 | bytea | Patient name; associated data = patient ID (a ciphertext copied to another row does not decrypt) |
| `name_index` | varchar(64), indexed | `HMAC-SHA256(INDEX_KEY, normalized name)` — exact-match blind index (ADR-001) |
| `created_at` | timestamptz | |

## `devices`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | varchar(64) PK | Device ID sent by the bedside device / simulator |
| `patient_id` | varchar(64) FK → patients.id, **unique**, not null | 1:1 pairing (REQ-013, RCM-008): one device ↔ one patient |
| `paired_at` | timestamptz | |

## `readings`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | integer PK | |
| `patient_id` | varchar(64) FK → patients.id | Taken from the pairing, never from the request (RISK-008) |
| `device_id` | varchar(64) FK → devices.id | |
| `timestamp` | timestamptz | Device measurement time (UTC); index `(patient_id, timestamp)` for "newest first" |
| `received_at` | timestamptz | Server receive time (for the data-loss check REQ-003 in Sprint 3) |
| `valid` | boolean | `false` = failed the REQ-002 plausibility check; never forwarded to the Alarm Engine |
| `vitals_enc` 🔒 | bytea | JSON `{"dia_bp","hr","spo2","sys_bp"}`; associated data = patient ID + device ID |

## `hazard_events` (ARC-004 v0)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | integer PK | |
| `timestamp` | timestamptz | Detection time (UTC) |
| `patient_id` | varchar(64) FK → patients.id, nullable | `null` when unknown (unpaired device) |
| `device_id` | varchar(64), nullable, **no FK** | Unpaired devices are not in `devices` |
| `event_type` | varchar(32), indexed | IMPLAUSIBLE_VALUE · UNPAIRED_DEVICE · DATA_LOSS · ARTEFACT_SUSPECTED · AUTH_FAILURE |
| `risk_id` | varchar(16) | Derived from `event_type` by the hazard log (RISK-002/008/001/002/006) |
| `detail` | text | Rule that was violated and the reading ID — **never** vital values or names |

## Not in v1 (planned)

- Sprint 3: `users` (ARC-005, Argon2 hashes), `audit_log` (ARC-006, append-only: UPDATE/DELETE rejected — TC-011), `alarms` (ARC-003 persistence, acknowledgement REQ-007), `thresholds` per patient (REQ-006).
- Schema migrations (Alembic) once the schema changes after the architecture freeze; until then `create_all` only creates missing tables.
- Device unpairing / re-pairing (Admin, with audit entry).

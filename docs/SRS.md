# MediTrace — Software Requirements Specification (SRS)

| Field | Value |
| --- | --- |
| Document ID | MT-SRS |
| Version | 2.0 |
| Date | 2026-11-14 |
| Author | Barış Bağbekleyen (Project & Standards Lead) |
| Reviewers | Team review via pull request (PLN-01) |
| Status | Released for Sprint 3 (architecture frozen at end of Sprint 2) |
| Standards | IEC 62304:2006+A1:2015 §5.2, IEEE 29148, ISO 14971:2019 |

## Change history

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | 2026-10-31 | Barış Bağbekleyen | Initial draft in Progress Report 1, Annex C.1: 17 requirements (REQ-001 – REQ-017), one-line statements, priorities Mandatory / Important / Optional. |
| 2.0 | 2026-11-14 | Barış Bağbekleyen | Every requirement rewritten in IEEE 29148 "shall" form with acceptance criteria, verification method, test ID and architecture components. Priorities renamed to Must / Should / Optional. REQ-002: diastolic range (20–200 mmHg) and the rule systolic > diastolic added. REQ-004: sharpened to "≥ 99 % within 3 s at 20 patients × 1 reading/s". REQ-007: acknowledgement restricted to Nurse/Doctor. REQ-016: v0 output is Markdown, PDF follows in R4. New requirements REQ-018, REQ-019, REQ-020, REQ-022, REQ-023, REQ-024; REQ-021 reserved. Requirement quality checklist added (§5). |

> **Educational project.** MediTrace uses simulated data only. Threshold values in this document are educational defaults and are not clinical advice.

---

## 1. Purpose and scope

### 1.1 Purpose
This SRS defines the software requirements of **MediTrace**, a central vital-sign monitoring and data management system. It is the requirements baseline for IEC 62304 §5.2 and the input for architecture (§5.3), verification (§5.5–5.7) and the risk management file (ISO 14971). Every requirement has a unique `REQ-xxx` identifier that is traced to risks (`RISK-xxx`), architecture components (`ARC-xxx`) and test cases (`TC-xxx`).

### 1.2 Product scope
- **What it does:** MediTrace collects heart rate (HR), systolic and diastolic blood pressure and SpO₂ from simulated bedside devices once per second per patient, validates every reading, stores data encrypted, raises prioritized smart alarms and logs hazardous events and every data access.
- **Intended use:** a **secondary (central) monitor** for a **general hospital ward**. Bedside monitors keep their own alarms and nurses perform periodic rounds; these two external risk control measures are the reason for the safety classification below.
- **Software safety class: B** (IEC 62304 §4.3) — the software can contribute to a hazardous situation that results in non-serious injury. If MediTrace were used as the primary alarm system or in an intensive care unit, it would be **Class C** (recorded assumption in the risk file).
- **Out of scope:** real medical devices and HL7/FHIR interfaces, diagnosis or treatment advice, mobile app, CE/MDR certification and clinical validation, a complete IEC 62366 usability file.

### 1.3 Assumptions and constraints
- One ward on a local network; up to 20 monitored patients at the same time.
- The Device Simulator represents real device data formats and failure modes (normal, boundary, disconnection, artefact, unpaired device).
- Alarms supplement and never replace clinical observation.
- Technology constraints (from the architecture, frozen at the end of Sprint 2): Python 3.12 / FastAPI, PostgreSQL 16 (SQLite in tests), React + TypeScript dashboard, WebSocket for live alarms.

---

## 2. Definitions

### 2.1 Identification scheme

| Prefix | Meaning | Example |
| --- | --- | --- |
| `REQ-xxx` | Software requirement (this document) | REQ-015 |
| `RISK-xxx` | Hazard / hazardous situation in the ISO 14971 risk register | RISK-009 |
| `RCM-xxx` | Risk control measure | RCM-002b |
| `ARC-xxx` | Architecture component (software item) | ARC-003 |
| `TC-xxx` | Test case; the number equals the requirement it verifies (TC-015 verifies REQ-015) | TC-015 |
| `RSK-xx` | Project / process issue (not a product risk) | RSK-08 |

IDs are never renumbered. REQ-021 and TC-021 are reserved and unused.

### 2.2 Requirement attributes

| Attribute | Allowed values |
| --- | --- |
| Type | Functional, Safety, Performance, Security, Reliability, Usability, Compliance (a requirement that implements a risk control measure is typed **Safety** or **Security**) |
| Priority | **Must** (required for release v1.0), **Should** (planned, may be descoped with a documented decision), **Optional** (only if time allows in R4) |
| Verification | **Test** (automated or scripted), **Inspection** (review of code/data), **Analysis** (measurement evaluation), **Demonstration** (observed walkthrough) |

### 2.3 Roles

| Role | Responsibilities |
| --- | --- |
| Doctor | Monitors patients, acknowledges alarms, **only role that changes per-patient thresholds**, reads the hazard log |
| Nurse | Monitors patients, acknowledges alarms |
| Admin | Manages users and device pairing; no access to patient vital data |
| Auditor | Read-only access to the audit log and hazard log |

Role permission matrix (implemented by ARC-005 in Sprint 3, verified by TC-009):

| Action | Admin | Doctor | Nurse | Auditor |
| --- | --- | --- | --- | --- |
| View patients, vitals, alarms | – | ✓ | ✓ | – |
| Acknowledge alarm | – | ✓ | ✓ | – |
| Change thresholds | – | ✓ | – | – |
| Pair devices, manage users | ✓ | – | – | – |
| Read audit log | – | – | – | ✓ |
| Read hazard log | – | ✓ | – | ✓ |

### 2.4 Default alarm thresholds (educational defaults, configurable per patient)

A value **equal to** a limit is normal; a violation is strictly `<` or `>`.

| Vital | Non-critical (MEDIUM after 5 consecutive readings) | Critical (immediate HIGH) |
| --- | --- | --- |
| SpO₂ | < 92 % | < 85 % |
| HR | < 50 or > 120 bpm | < 40 or > 150 bpm |
| Systolic BP | < 90 or > 180 mmHg | none in v1 (non-critical only) |

### 2.5 Shared data contract
Field names are identical in backend, alarm engine and frontend. Timestamps are ISO 8601 in **UTC**.

```text
Reading (in, POST /readings):  {device_id, timestamp, hr, sys_bp, dia_bp, spo2}
Reading (out):                 {patient_id, device_id, timestamp, hr, sys_bp, dia_bp, spo2, valid}
Alarm:   {id, patient_id, kind: THRESHOLD|DATA_LOSS|ARTEFACT_SUSPECTED, priority: HIGH|MEDIUM|LOW,
          vital: hr|sys_bp|dia_bp|spo2|null, value, timestamp, state: ACTIVE|ACKNOWLEDGED|RESOLVED,
          acknowledged_by, acknowledged_at, risk_id}
HazardEvent: {id, timestamp, patient_id|null, device_id|null,
          event_type: IMPLAUSIBLE_VALUE|UNPAIRED_DEVICE|DATA_LOSS|ARTEFACT_SUSPECTED|AUTH_FAILURE, risk_id, detail}
```

Hazard event → risk mapping: IMPLAUSIBLE_VALUE → RISK-002 · UNPAIRED_DEVICE → RISK-008 · DATA_LOSS → RISK-001 · ARTEFACT_SUSPECTED → RISK-002 · AUTH_FAILURE → RISK-006.

### 2.6 Other terms
- **Valid reading:** a reading that passed the plausibility check of REQ-002 and came from a paired device (REQ-013).
- **Validation complete:** the moment the reading that makes an alarm condition true has been validated; for a non-critical violation this is the 5th consecutive violating reading (REQ-015).
- **p95 / p99:** the 95th / 99th percentile of a set of measured durations.

---

## 3. Requirements

Format of each block (parsed by the Compliance Reporter, see `tools/trace/trace.py`): a level-3 heading `### REQ-xxx — <title>` followed by an attribute table with at least the rows `Priority` and `Related risks`.

### 3.1 Data acquisition and validation

### REQ-001 — Vital-sign simulation

| Attribute | Value |
| --- | --- |
| Statement | The Device Simulator shall send one reading containing HR, systolic BP, diastolic BP and SpO₂ for each simulated patient once per second. |
| Type | Functional |
| Priority | Must |
| Source | Stakeholder: ward data collection (Progress Report 1, product definition) |
| Related risks | – |
| Acceptance criteria | (1) Simulator started with 3 patients and run for 10 s → each patient produces 10 readings (± 1 for the window edges). (2) Every reading contains `device_id`, a UTC ISO 8601 `timestamp`, `hr`, `sys_bp`, `dia_bp` and `spo2`. (3) Consecutive readings of one patient are 1 s apart. (4) Scenarios normal, boundary, disconnection, artefact and unpaired device are selectable. |
| Verification | Test — TC-001 |
| Architecture | ARC-001 Device Simulator |

### REQ-002 — Plausibility check

| Attribute | Value |
| --- | --- |
| Statement | The Ingestion & Validation component shall mark a reading invalid when HR is outside 20–300 bpm, SpO₂ is outside 50–100 %, systolic BP is outside 40–300 mmHg, diastolic BP is outside 20–200 mmHg, or systolic BP is not greater than diastolic BP; an invalid reading shall be excluded from alarm evaluation and written to the hazard log. |
| Type | Safety |
| Priority | Must |
| Source | RISK-002 (RCM-002 plausibility check) |
| Related risks | RISK-002 |
| Acceptance criteria | (1) Reading with HR 350 → stored with `valid = false`, not passed to the Alarm Engine, one hazard event `IMPLAUSIBLE_VALUE` with `risk_id = RISK-002`. (2) Range limits are inclusive: HR 20 and 300, SpO₂ 50 and 100, systolic 40 and 300, diastolic 20 and 200 are valid; HR 19 / 301, SpO₂ 49 / 101, systolic 39 / 301, diastolic 19 / 201 are invalid. (3) Systolic 120 / diastolic 120 → invalid; systolic 121 / diastolic 120 → valid. (4) No alarm is raised from an invalid reading. (5) The additional rate-of-change artefact check RCM-002b (ARC-003, limits defined in `docs/risk/risk-register.md`) flags a suspected artefact as `ARTEFACT_SUSPECTED` (LOW, informational) and does not count it toward the REQ-015 window. |
| Verification | Test — TC-002 |
| Architecture | ARC-002 Ingestion & Validation, ARC-003 Alarm Engine (RCM-002b), ARC-004 Hazard Log |

### REQ-013 — Device–patient pairing

| Attribute | Value |
| --- | --- |
| Statement | The system shall associate each device with exactly one patient and shall reject readings from an unpaired device and write a hazard event for each rejected reading. |
| Type | Safety |
| Priority | Must |
| Source | RISK-008 (RCM-008 1:1 device–patient pairing) |
| Related risks | RISK-008 |
| Acceptance criteria | (1) `POST /devices/pair` pairs device D1 with patient P1 → readings from D1 are stored with `patient_id = P1`. (2) Pairing D1 with a second patient P2 while it is paired with P1 is rejected with an HTTP 4xx status and the existing pairing is unchanged. (3) `POST /readings` from unpaired device D9 → HTTP 4xx, the reading is not stored and not forwarded to the Alarm Engine, one hazard event `UNPAIRED_DEVICE` with `device_id = D9`, `patient_id = null`, `risk_id = RISK-008`. |
| Verification | Test — TC-013 |
| Architecture | ARC-002 Ingestion & Validation, ARC-004 Hazard Log, ARC-007 Encrypted Data Layer |

### REQ-018 — Ingestion latency *(new in v2.0)*

| Attribute | Value |
| --- | --- |
| Statement | The Ingestion & Validation component shall validate and forward each reading within 200 ms (p95) at a load of 20 patients × 1 reading/s. |
| Type | Performance |
| Priority | Should |
| Source | RISK-003 (contributes to the REQ-004 deadline) |
| Related risks | RISK-003 |
| Acceptance criteria | Load of 20 simulated patients × 1 reading/s for 10 min (12 000 readings): the time from receipt of `POST /readings` to hand-over of the validated reading to the Alarm Engine and storage is ≤ 200 ms for at least 95 % of readings. |
| Verification | Test — TC-018 |
| Architecture | ARC-002 Ingestion & Validation |

### REQ-019 — Robustness against malformed input *(new in v2.0)*

| Attribute | Value |
| --- | --- |
| Statement | The Ingestion & Validation component shall continue processing valid readings without crashing when 10 % of the input readings are malformed or out of range during a 1-hour run. |
| Type | Reliability |
| Priority | Must |
| Source | RISK-002 |
| Related risks | RISK-002 |
| Acceptance criteria | 1-hour fault-injection run at 20 patients × 1 reading/s (72 000 readings), 10 % of them malformed (missing fields, wrong types, invalid JSON) or out of range: (1) 0 crashes / unhandled exceptions / restarts of the service; (2) every valid reading is stored and forwarded; (3) every out-of-range reading produces an `IMPLAUSIBLE_VALUE` hazard event; malformed requests are answered with an HTTP 4xx status. |
| Verification | Test — TC-019 (fault injection) |
| Architecture | ARC-002 Ingestion & Validation, ARC-004 Hazard Log |

### 3.2 Alarms

### REQ-003 — Data-loss alarm

| Attribute | Value |
| --- | --- |
| Statement | The Alarm Engine shall raise a HIGH-priority `DATA_LOSS` technical alarm when no valid reading has been received from a monitored patient for 10 s. |
| Type | Safety |
| Priority | Must |
| Source | RISK-001 (RCM-001 data-loss alarm after 10 s) |
| Related risks | RISK-001 |
| Acceptance criteria | (1) Last valid reading at t₀; check at t₀ + 9 s → no alarm; check at t₀ + 10 s → exactly one alarm `kind = DATA_LOSS`, `priority = HIGH`, `risk_id = RISK-001`, and one hazard event `DATA_LOSS`. (2) Repeated checks during the same silence do not create a second alarm. (3) Invalid readings do not reset the 10 s timer. (4) Only the silent patient gets the alarm. (5) When valid data resumes, the alarm condition clears; a new 10 s silence raises a new alarm. |
| Verification | Test — TC-003 |
| Architecture | ARC-003 Alarm Engine, ARC-004 Hazard Log |

### REQ-004 — Alarm display deadline

| Attribute | Value |
| --- | --- |
| Statement | The system shall display a threshold alarm on the dashboard within 3 s after validation of the triggering reading completes, for at least 99 % of alarms, at a load of 20 patients × 1 reading/s. |
| Type | Performance |
| Priority | Must |
| Source | RISK-003 (RCM-003 3 s deadline) |
| Related risks | RISK-003 |
| Acceptance criteria | Load test with 20 simulated patients × 1 reading/s for 10 min and scripted violations producing at least 200 threshold alarms: for ≥ 99 % of alarms the time from "validation complete" (§2.6) to the alarm being rendered on the dashboard (WebSocket message received and alarm shown) is ≤ 3 s. For a non-critical alarm the clock starts at the 5th consecutive violating reading (see §5.2). |
| Verification | Test — TC-004 (load test) |
| Architecture | ARC-002 Ingestion & Validation, ARC-003 Alarm Engine, ARC-008 Monitoring Dashboard |

### REQ-005 — Alarm priorities

| Attribute | Value |
| --- | --- |
| Statement | The system shall assign every alarm one of the priorities HIGH, MEDIUM or LOW and shall present a HIGH alarm with both a visual and an audible alert. |
| Type | Functional |
| Priority | Must |
| Source | RISK-003 (RCM-003 audible HIGH alarm), IEC 60601-1-8 |
| Related risks | RISK-003 |
| Acceptance criteria | (1) Every alarm object has `priority ∈ {HIGH, MEDIUM, LOW}`. (2) With one active alarm of each priority, the alarm screen lists them in the order HIGH, MEDIUM, LOW. (3) A HIGH alarm shows a banner in the HIGH colour and plays the audible alarm signal. (4) MEDIUM and LOW alarms are shown with their own distinct colours. |
| Verification | Test — TC-005 |
| Architecture | ARC-003 Alarm Engine, ARC-008 Monitoring Dashboard |

### REQ-007 — Alarm acknowledgement

| Attribute | Value |
| --- | --- |
| Statement | The system shall keep a HIGH alarm in state ACTIVE until a Nurse or Doctor acknowledges it and shall record the acknowledging user and the acknowledgement time. |
| Type | Safety |
| Priority | Must |
| Source | RISK-005 (RCM-005 acknowledgement required) |
| Related risks | RISK-005 |
| Acceptance criteria | (1) A HIGH alarm remains `ACTIVE` and visible even after the vital returns to normal, until it is acknowledged. (2) `POST /alarms/{id}/ack` by a Nurse or Doctor → `state = ACKNOWLEDGED`, `acknowledged_by` = that user, `acknowledged_at` = UTC time of the request. (3) The same request by Admin or Auditor → HTTP 403, alarm stays `ACTIVE`. (4) The acknowledgement is written to the audit log. |
| Verification | Test — TC-007 |
| Architecture | ARC-003 Alarm Engine, ARC-005 Auth & RBAC, ARC-006 Audit Log, ARC-008 Monitoring Dashboard |

### REQ-015 — Smart alarm validation with critical bypass

| Attribute | Value |
| --- | --- |
| Statement | The Alarm Engine shall raise a MEDIUM alarm for a non-critical threshold violation only after 5 consecutive valid violating readings (5 s), and shall raise a HIGH alarm immediately for a single valid reading beyond a critical threshold. |
| Type | Safety |
| Priority | Must |
| Source | RISK-005 (RCM-005 smart validation against alarm fatigue), RISK-009 (RCM-009 5 s window + critical bypass) |
| Related risks | RISK-005, RISK-009 |
| Acceptance criteria | With default thresholds (§2.4): (1) 4 consecutive readings SpO₂ 90 → no alarm; the 5th → exactly one MEDIUM `THRESHOLD` alarm. (2) A normal reading between violations resets the counter. (3) A persisting violation does not raise the MEDIUM alarm again every second. (4) One reading SpO₂ 84 or HR 151 or HR 39 → immediate HIGH alarm. (5) Boundary: SpO₂ 92 is normal, 91 counts as a violation; SpO₂ 85 is not critical, 84 is critical; HR 120 normal, 121 violation; HR 150 not critical, 151 critical. (6) Systolic BP has no critical level in v1: a single systolic 250 gives no HIGH alarm. (7) Each vital has its own counter. |
| Verification | Test — TC-015 |
| Architecture | ARC-003 Alarm Engine |

### REQ-017 — Trend alert

| Attribute | Value |
| --- | --- |
| Statement | The Alarm Engine shall raise a LOW-priority trend alert when SpO₂ deteriorates steadily by more than 4 points within 60 min before any alarm threshold is crossed. |
| Type | Functional |
| Priority | Optional |
| Source | Stakeholder: earlier warning of slow deterioration (distinguishing feature 3) |
| Related risks | – |
| Acceptance criteria | (1) SpO₂ decreasing steadily from 98 to 93 over 60 min (5 points) → exactly one LOW trend alert. (2) SpO₂ decreasing from 98 to 94 over 60 min (4 points) → no alert. (3) A trend alert never changes the priority of a threshold alarm. Implemented only if time allows in R4. |
| Verification | Test — TC-017 |
| Architecture | ARC-003 Alarm Engine, ARC-008 Monitoring Dashboard |

### REQ-024 — Alarm engine reliability and restart *(new in v2.0)*

| Attribute | Value |
| --- | --- |
| Statement | The Alarm Engine shall run for 8 h at 20 patients × 1 reading/s with 0 crashes and shall lose 0 active alarms after a restart. |
| Type | Reliability |
| Priority | Must |
| Source | RISK-001, RISK-005 |
| Related risks | RISK-001, RISK-005 |
| Acceptance criteria | (1) 8-hour soak test at 20 patients × 1 reading/s (576 000 readings): 0 crashes, 0 unhandled exceptions. (2) With N ≥ 3 active alarms (including one HIGH not yet acknowledged), the backend is restarted → after restart the same N alarms are present with the same `id`, `priority` and `state`. |
| Verification | Test — TC-024 (soak + restart) |
| Architecture | ARC-003 Alarm Engine, ARC-007 Encrypted Data Layer |

### 3.3 Security and access control

### REQ-006 — Doctor-only threshold changes

| Attribute | Value |
| --- | --- |
| Statement | The system shall allow only users with the Doctor role to change per-patient alarm thresholds, shall reject the request with HTTP 403 for every other role, and shall write every threshold change to the audit log. |
| Type | Security |
| Priority | Must |
| Source | RISK-004 (RCM-004 Doctor-only + audit) |
| Related risks | RISK-004 |
| Acceptance criteria | (1) `PUT /patients/{id}/thresholds` as Doctor → HTTP 200, the new thresholds are used by the Alarm Engine for the next reading of that patient only, and one audit entry contains user, UTC time, patient, old and new values. (2) The same request as Nurse, Admin or Auditor → HTTP 403 and thresholds unchanged. (3) Inconsistent thresholds (e.g. low ≥ high, critical inside non-critical) are rejected. |
| Verification | Test — TC-006 |
| Architecture | ARC-005 Auth & RBAC, ARC-006 Audit Log, ARC-003 Alarm Engine |

### REQ-008 — Authentication and lockout

| Attribute | Value |
| --- | --- |
| Statement | The system shall authenticate users with username and password, shall store passwords only as Argon2 hashes, and shall lock an account for 15 min after 5 consecutive failed login attempts. |
| Type | Security |
| Priority | Must |
| Source | RISK-006 (RCM-006 Argon2, lockout) |
| Related risks | RISK-006 |
| Acceptance criteria | (1) The user table contains only Argon2 hashes (`$argon2id$…`), never a plaintext password. (2) 5 wrong passwords in a row → the 6th attempt is rejected even with the correct password; each failure creates an `AUTH_FAILURE` hazard event (`risk_id = RISK-006`). (3) After 15 min the correct password is accepted again. (4) A successful login before the 5th failure resets the counter. |
| Verification | Test — TC-008 |
| Architecture | ARC-005 Auth & RBAC, ARC-004 Hazard Log, ARC-007 Encrypted Data Layer |

### REQ-009 — Role-based access control

| Attribute | Value |
| --- | --- |
| Statement | The system shall support the roles Admin, Doctor, Nurse and Auditor and shall check every API endpoint against the role permission matrix of §2.3. |
| Type | Security |
| Priority | Must |
| Source | RISK-006 (RCM-006 RBAC), KVKK (Law 6698) |
| Related risks | RISK-006 |
| Acceptance criteria | For every pair (endpoint, role): an allowed pair (✓ in §2.3) returns a 2xx status, a forbidden pair returns HTTP 403, and a request without a valid token returns HTTP 401. `GET /health` is the only endpoint without authentication. |
| Verification | Test — TC-009 (endpoint × role matrix) |
| Architecture | ARC-005 Auth & RBAC |

### REQ-010 — Encryption at rest

| Attribute | Value |
| --- | --- |
| Statement | The Encrypted Data Layer shall store patient identity data and vital-sign values encrypted with AES-256-GCM. |
| Type | Security |
| Priority | Must |
| Source | RISK-007 (RCM-007 AES-256-GCM), KVKK (Law 6698) |
| Related risks | RISK-007 |
| Acceptance criteria | (1) After storing patient "Test Patient" and a reading HR 77, a raw dump of the database contains neither the string "Test Patient" nor the stored values in plaintext. (2) Reading through ARC-007 returns the original values. (3) A modified ciphertext byte causes a decryption error (GCM authentication tag), not wrong data. (4) Patient search works through the HMAC blind index (PLN-05, closes RSK-06) without decrypting all rows. (5) No encryption key is committed to the repository. |
| Verification | Test — TC-010; Inspection of the repository for keys |
| Architecture | ARC-007 Encrypted Data Layer |

### REQ-011 — Append-only audit log

| Attribute | Value |
| --- | --- |
| Statement | The system shall write every access to and change of patient data, thresholds, users and pairings to an append-only audit log. |
| Type | Security/Compliance |
| Priority | Must |
| Source | RISK-007 (RCM-007 append-only audit), KVKK (Law 6698) |
| Related risks | RISK-007 |
| Acceptance criteria | (1) Each API request that reads or changes such data creates one audit entry with user, role, action, resource and UTC time. (2) An `UPDATE` or `DELETE` on the audit table is rejected by the database. (3) Audit entries are readable only by the Auditor role. |
| Verification | Test — TC-011 |
| Architecture | ARC-006 Audit Log, ARC-007 Encrypted Data Layer |

### REQ-020 — Encryption overhead *(new in v2.0)*

| Attribute | Value |
| --- | --- |
| Statement | The Encrypted Data Layer shall add at most 20 ms (p95) per read or write operation for encryption or decryption. |
| Type | Performance |
| Priority | Should |
| Source | RISK-003 (encryption must not endanger the REQ-004 deadline) |
| Related risks | RISK-003 |
| Acceptance criteria | Benchmark of 10 000 single-reading writes and 10 000 reads with and without encryption on the CI runner: the difference between encrypted and plaintext operation is ≤ 20 ms at p95 for both reads and writes. |
| Verification | Test — TC-020 (benchmark) |
| Architecture | ARC-007 Encrypted Data Layer |

### 3.4 Hazard log, dashboard and usability

### REQ-012 — Hazard log

| Attribute | Value |
| --- | --- |
| Statement | The Hazard Log shall record every hazardous event with its time, patient, event type and related RISK ID. |
| Type | Functional |
| Priority | Must |
| Source | All risks (ISO 14971 §10 production and post-production information) |
| Related risks | RISK-001, RISK-002, RISK-003, RISK-004, RISK-005, RISK-006, RISK-007, RISK-008, RISK-009, RISK-010 |
| Acceptance criteria | (1) For each event type of §2.5, triggering the event creates exactly one `HazardEvent` with `timestamp` (UTC), `patient_id` (or `null` when unknown, e.g. unpaired device), `device_id`, `event_type`, the `risk_id` given by the mapping in §2.5 and a `detail` text. (2) Hazard events are readable by Doctor and Auditor only. |
| Verification | Test — TC-012 |
| Architecture | ARC-004 Hazard Log |

### REQ-014 — 24-hour trend chart

| Attribute | Value |
| --- | --- |
| Statement | The patient detail screen shall show the readings of the last 24 h of the selected patient as a time-series chart. |
| Type | Functional |
| Priority | Should |
| Source | Stakeholder: Doctor / Nurse need to see recent history |
| Related risks | – |
| Acceptance criteria | With readings seeded over the last 30 h, the chart shows exactly the readings with timestamps in [now − 24 h, now], in time order, for HR, systolic BP, diastolic BP and SpO₂; invalid readings are not plotted as values. |
| Verification | Test — TC-014 |
| Architecture | ARC-008 Monitoring Dashboard, ARC-007 Encrypted Data Layer |

### REQ-022 — Acknowledgement usability *(new in v2.0)*

| Attribute | Value |
| --- | --- |
| Statement | The dashboard shall allow a Nurse to acknowledge an active alarm with at most 2 clicks within at most 5 s. |
| Type | Usability |
| Priority | Should |
| Source | RISK-005 (alarm handling must be fast and error-free) |
| Related risks | RISK-005 |
| Acceptance criteria | Walkthrough with 5 users in the Nurse role, each starting from the patient list when a HIGH alarm appears: every user acknowledges the alarm with ≤ 2 clicks and within ≤ 5 s from its appearance; clicks and times are recorded. |
| Verification | Demonstration (usability walkthrough) — TC-022 |
| Architecture | ARC-008 Monitoring Dashboard, ARC-003 Alarm Engine |

### REQ-023 — Chart rendering time *(new in v2.0)*

| Attribute | Value |
| --- | --- |
| Statement | The patient detail screen shall render the 24-hour chart within 2 s on a standard laptop. |
| Type | Performance |
| Priority | Should |
| Source | Stakeholder: usable patient detail screen |
| Related risks | – |
| Acceptance criteria | Patient with 24 h of readings at 1 reading/s (86 400 readings), standard laptop = 4-core CPU, 8 GB RAM, current Chrome: in each of 5 runs the time from opening the patient detail screen to the fully rendered chart (browser performance timing) is ≤ 2 s. |
| Verification | Test — TC-023 |
| Architecture | ARC-008 Monitoring Dashboard |

### 3.5 Compliance

### REQ-016 — Compliance reporter

| Attribute | Value |
| --- | --- |
| Statement | The Compliance Reporter shall generate the traceability matrix and an IEC 62304 summary from the REQ/RISK/TC tags in the SRS, source code, tests and CI results, and shall flag every requirement whose tests are missing or failing. |
| Type | Compliance |
| Priority | Must |
| Source | RISK-010 (RCM-010 report only from real CI results), IEC 62304 §7.3.3 traceability |
| Related risks | RISK-010 |
| Acceptance criteria | (1) Given an SRS with a Must requirement that no test references → status `NO TEST`. (2) Given a JUnit result in which one test of a requirement failed → status `FAILING`. (3) A requirement is shown `OK` only when at least one test exists and all of its tests passed in the given results. (4) Output `docs/traceability.md` contains the table `REQ | Priority | Risks | Implemented in | Tests | Status`, a summary line and the generation time. v0 (Sprint 2) writes Markdown; the PDF with the IEC 62304 summary follows in R4. |
| Verification | Test — TC-016 |
| Architecture | ARC-009 Compliance Reporter (CI tool, not runtime) |

### REQ-021 — Reserved

| Attribute | Value |
| --- | --- |
| Statement | Reserved — this ID is intentionally unused and will not be reassigned. |
| Priority | Reserved |
| Related risks | – |

---

## 4. Traceability

The traceability matrix REQ → RISK → ARC (implementation) → TC → test result is **generated** by the Compliance Reporter (ARC-009, REQ-016) and stored in [`docs/traceability.md`](traceability.md). Do not edit that file by hand; regenerate it with:

```bash
pytest -q --junitxml=report.xml
python -m tools.trace.trace --junit report.xml
```

Sources used by the generator:
- this SRS (`### REQ-xxx` blocks, `Priority` and `Related risks` rows);
- `# Implements REQ-xxx` comments in `backend/` and `simulator/`;
- the first docstring line `TC-xxx / REQ-xxx: …` of pytest tests and Vitest test names `TC-xxx / REQ-xxx: …` in `frontend/src/`;
- the pytest JUnit XML result.

Risk-side traceability (RISK → RCM → REQ) is maintained in the risk register `docs/risk/risk-register.md`.

---

## 5. Requirement quality checklist (IEEE 29148)

### 5.1 How each requirement was checked

Every requirement in §3 was reviewed against the IEEE 29148 characteristics of an individual requirement:

| Characteristic | Check applied in v2.0 |
| --- | --- |
| Necessary | Each requirement has a source: a RISK-xxx control measure or a named stakeholder need. Requirements without such a source were not added (scope creep control, RSK-05). |
| Unambiguous | One statement per block in "shall" form with a named subject (component or system). Numeric limits have units, boundary behaviour is stated (inclusive plausibility ranges; equal-to-threshold is normal), times are in UTC. |
| Singular | Each statement describes one capability. Where v1.0 combined a capability with a quality (e.g. alarm display + latency), the quality was kept measurable in the same block, and new qualities were split into separate requirements (REQ-018 – REQ-024). |
| Verifiable | Each block has acceptance criteria with concrete inputs and expected results and one verification method and test ID (TC number = REQ number). Vague words of v1.0 ("quickly", "appears") were replaced by numbers. |
| Traceable | Unique, never-renumbered IDs; each block lists related risks and ARC components; tests carry `TC-xxx / REQ-xxx` tags; the matrix is generated, not hand-written (§4). |
| Consistent | Values were cross-checked against the risk register, the architecture data contract and the alarm thresholds table; the conflict below was resolved explicitly. |
| Feasible | Performance targets (REQ-004, REQ-018, REQ-020, REQ-023) are sized for 20 patients × 1 reading/s on the planned stack; REQ-017 is Optional because of schedule risk. |

### 5.2 Consistency decision: REQ-004 vs REQ-015 (resolution of RSK-08)

REQ-015 waits for 5 consecutive readings (5 s) before raising a non-critical alarm, while REQ-004 demands that an alarm is shown within 3 s. Read naively, the two requirements contradict each other. The team resolved this in Sprint 1 (RSK-08) and v2.0 states it explicitly:

1. **The 3 s of REQ-004 are counted from the end of validation**, i.e. from the reading that completes the alarm condition (the 5th consecutive violating reading for a non-critical violation; the single reading for a critical value). REQ-004 limits system latency, not clinical confirmation time.
2. **Critical values bypass the 5-reading window** (REQ-015) and alarm immediately, so a dangerous value reaches the dashboard within ≤ 3 s of its arrival.
3. The delay created by the smart validation is itself a risk (**RISK-009**, ISO 14971 §7.5, risk arising from a risk control measure) and is controlled by RCM-009 (short 5 s window + critical bypass).

### 5.3 Other decisions recorded in v2.0
- REQ-002 plausibility ranges are inclusive at both ends, while REQ-015 thresholds are strict (`<`, `>`), so a value equal to an alarm limit is normal.
- REQ-007 latching: a HIGH alarm stays ACTIVE after the vital returns to normal until it is acknowledged (IEC 60601-1-8 latching behaviour).
- Threshold and timing values (10 s, 3 s, 5 readings, 5 attempts, 15 min) are educational defaults reviewed in the risk register; changing any of them requires an SRS version change and a risk review.

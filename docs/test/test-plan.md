# MediTrace — Software Test Plan (MT-STP)

| | |
| --- | --- |
| Document | MT-STP, version 1.0 (Sprint 2, PLN-07) |
| Owner | Mert Eser (Frontend & Test Lead) |
| Standards | IEC 62304:2006+A1:2015 §5.5 (unit verification), §5.6 (integration testing), §5.7 (system testing), §9 (problem resolution); IEEE 1012 (V&V, integrity levels) |
| Related documents | `docs/SRS.md` (requirements and acceptance criteria), `docs/SDP.md` §8 (verification strategy summary), `docs/risk/` (risk register), `docs/traceability.md` (generated), `docs/test/ui-wireframes.md` |
| Safety class | B (IEC 62304 §4.3) |

This plan says **what** is tested, **at which level**, **with which tools**, **by whom** and **when**, and
how test results become traceability evidence. The acceptance criteria themselves are in the SRS; this
plan does not repeat them in full.

---

## 1. Scope and test items

| ID | Component | Location | Integrity level (§3) | Main test levels | First tests |
| --- | --- | --- | --- | --- | --- |
| ARC-001 | Device Simulator | `simulator/` | 2 | unit, system | R2 |
| ARC-002 | Ingestion & Validation | `backend/app/ingestion/` | **3** | unit, integration, performance, fault injection | R2 |
| ARC-003 | Alarm Engine | `backend/app/alarm/` | **3** | unit, integration, soak | R2 |
| ARC-004 | Hazard Log | `backend/app/hazard/` | 2 | unit, integration | R2 (v0), R3 |
| ARC-005 | Auth & RBAC | `backend/app/auth/` | 2 | unit, integration (endpoint × role) | R3 |
| ARC-006 | Audit Log | `backend/app/audit/` | 2 | integration (append-only at DB level) | R3 |
| ARC-007 | Encrypted Data Layer | `backend/app/storage/` | 2 | unit, inspection, benchmark | R2 |
| ARC-008 | Monitoring Dashboard | `frontend/` | 2 | unit/component (Vitest), system, usability | R2 |
| ARC-009 | Compliance Reporter | `tools/trace/` | 2 | unit | R2 |

**Out of scope:** real medical devices, HL7/FHIR, clinical validation, a full IEC 62366 usability file,
load beyond 20 patients × 1 Hz (the specified ward size).

## 2. Test levels

| Level | What | Tools | Environment | Who | When |
| --- | --- | --- | --- | --- | --- |
| **Unit** (§5.5) | Functions/classes in isolation, boundaries, error paths | pytest; Vitest + React Testing Library | local + CI | author of the code | every PR from R2 |
| **Integration** (§5.6) | API endpoints with the real components behind them, SQLite test DB, ingestion → alarm engine → hazard log, endpoint × role matrix | pytest + FastAPI `TestClient` (httpx), SQLite | local + CI | Bahadır (API), Ege (alarm wiring), Mert (review) | R3 |
| **System** (§5.7) | Simulator + full stack (backend, PostgreSQL, dashboard) as in operation | Docker Compose, simulator scenarios, browser | local (Docker) | Mert | R4 |
| **Performance / soak** | REQ-004 alarm display deadline, REQ-018 ingestion latency, REQ-020 encryption overhead, REQ-023 chart time, REQ-024 8-h soak + restart | simulator in load mode, timing logs, browser performance timing | local (Docker) / CI runner for benchmarks | Mert (REQ-004/023/024), Bahadır (REQ-018/020) | R3 (REQ-020), R4 |
| **Fault injection** | REQ-019: 10 % malformed/out-of-range input for 1 h | simulator fault scenario | local (Docker) | Bahadır, Mert | R4 |
| **Usability walkthrough** | REQ-022: 5 users in the Nurse role acknowledge a HIGH alarm starting from the patient list; clicks and seconds recorded | dashboard, stopwatch/screen recording, form in `docs/test/` | in person | Mert (facilitator) | R4 |

## 3. Integrity levels and coverage targets (IEEE 1012, team decision)

| Integrity level | Components | Required verification | Coverage target |
| --- | --- | --- | --- |
| **3** | ARC-002 Ingestion & Validation, ARC-003 Alarm Engine | Independent PR review on **every** change (reviewer ≠ author), boundary tests for every limit in the SRS, detailed design (§5.4) | **branch coverage ≥ 80 %** |
| **2** | ARC-001, ARC-004 – ARC-009 | PR review | **line coverage ≥ 60 %** |

- **Measurement:** CI runs `pytest --cov=backend/app --cov-branch` (line *and* branch coverage per file in the
  job log). Dashboard coverage with `@vitest/coverage-v8` is added in Sprint 3 (new SOUP item, needs a PR).
- **Enforcement:** in Sprint 2 the targets are checked by the reviewer from the CI log. From Sprint 3, CI fails
  when ARC-002/ARC-003 are below 80 % branch coverage (`--cov-fail-under` per package or a small check
  script) — decision to be taken at the R3 planning meeting.
- Coverage is a minimum, not proof: a requirement is verified only by its tagged test cases (§4–5).

## 4. Traceability tagging convention

The Compliance Reporter (ARC-009, `tools/trace/trace.py`) parses these tags; a test without a tag is ignored
for traceability (it may still be a useful support test).

| Where | Format | Example |
| --- | --- | --- |
| pytest | **first line of the docstring** of each test function: `TC-xxx / REQ-xxx[, REQ-yyy]: <what>` | `"""TC-015 / REQ-015: 4 violating readings give no alarm, the 5th gives MEDIUM."""` |
| Vitest | test name **starts with** `TC-xxx / REQ-xxx:` in `frontend/src/**/*.test.ts(x)` | `it('TC-007 / REQ-007: HIGH alarm stays until acknowledged', …)` |
| Python source | comment above the implementing function/class | `# Implements REQ-015` / `# Controls RISK-005` |
| TypeScript source | comment in non-test `frontend/src/**/*.ts(x)` | `// Implements REQ-005` / `// Controls RISK-003` |

Rules:
1. **TC number = REQ number** (TC-015 verifies REQ-015). TC-021 / REQ-021 are reserved.
2. One requirement may have **several** tests with the same TC ID (e.g. boundary cases, UI and API part).
3. A test may name extra requirements after the first one (`TC-015 / REQ-015, REQ-003`); the TC number must
   match the first REQ.
4. **Do not tag a test with a requirement it does not really verify.** Example: hiding the *Acknowledge*
   button for the Auditor in the UI is not a verification of REQ-009 (server-side RBAC) — such tests stay
   untagged. Otherwise the compliance report could show a requirement as covered too early (RISK-010).
5. A requirement counts as verified only with a **real passing result** (CI JUnit file), see SDP §8 / RCM-010.
   Known limitation (Sprint 2): Vitest results are not yet read by the reporter (shown as
   *OK (frontend, not in JUnit)*), and a requirement whose acceptance criteria have a backend part (e.g. REQ-007
   `POST /alarms/{id}/ack`) or a demonstration (REQ-022) is shown as OK as soon as its frontend tests exist.
   These rows must be read as **partially verified** until the API / system tests of §5 exist (open point for
   Barış and Mert, Sprint 3).

## 5. Test cases

Level: U = unit, I = integration, S = system, P = performance/soak, D = demonstration (walkthrough).
Status = state at the end of Sprint 2 (14.11.2026) as seen on the pushed branches.

| TC | REQ | Level | Short procedure | Expected result | Owner | Sprint | Status (R2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | REQ-001 | U, S | Run the simulator with 3 patients for 10 s; inspect the emitted readings | 10 ± 1 readings per patient, 1 s apart, all fields of the data contract, UTC timestamps; scenarios selectable | Bahadır | R2 | pending (Bahadır's PR) |
| TC-002 | REQ-002 | U, I | Send readings at and just outside every plausibility limit (HR 20/300 vs 19/301, SpO₂ 50/100 vs 49/101, systolic 40/300, diastolic 20/200, systolic ≤ diastolic); HR 350 | Out-of-range → `valid = false`, not passed to the Alarm Engine, one `IMPLAUSIBLE_VALUE` hazard event (RISK-002); limits inclusive; RCM-002b artefact → LOW `ARTEFACT_SUSPECTED`, not counted for REQ-015 | Bahadır (range check), Ege (RCM-002b) | R2 | engine part: 7 tests on Ege's branch; range check pending |
| TC-003 | REQ-003 | U, I | Last valid reading at t₀; evaluate at t₀ + 9 s and t₀ + 10 s; invalid readings in between | No alarm at 9 s; exactly one HIGH `DATA_LOSS` alarm (RISK-001) and one hazard event at 10 s; no duplicate; invalid readings do not reset the timer | Ege (engine), Bahadır (hazard event, R3) | R2 / R3 | engine part: 7 tests on Ege's branch |
| TC-004 | REQ-004 | P | 20 patients × 1 Hz for 10 min with scripted violations (≥ 200 alarms); timestamp at "validation complete" and when the dashboard renders the alarm | ≥ 99 % of alarms shown ≤ 3 s after validation | Mert | R4 | planned (needs WebSocket, R3) |
| TC-005 | REQ-005 | U, S | One active alarm of each priority; HIGH alarm present | Alarm screen order HIGH, MEDIUM, LOW; HIGH: red banner + audible signal; MEDIUM/LOW distinct colours; every alarm has a valid priority | Mert (UI), Ege (engine priorities) | R2 | **UI: 4 Vitest tests passing**; engine priority test open (reporter finding, Barış's notes #5) |
| TC-006 | REQ-006 | I | `PUT /patients/{id}/thresholds` as each role; inconsistent thresholds | Doctor → 200 + audit entry with old/new values, applied to next reading; others → 403, unchanged; inconsistent → rejected | Bahadır | R3 | planned |
| TC-007 | REQ-007 | U, I | HIGH alarm active, vital returns to normal; acknowledge as Nurse/Doctor and as Admin/Auditor | Stays `ACTIVE` until acknowledged; ack records user + UTC time; Admin/Auditor → 403; audit entry written | Mert (UI), Bahadır (API) | R2 / R3 | **UI: 4 Vitest tests passing**; API part R3 |
| TC-008 | REQ-008 | I | 5 wrong passwords, then correct; wait 15 min (clock injected); inspect user table | Argon2id hashes only; 6th attempt rejected; `AUTH_FAILURE` hazard events; unlock after 15 min | Bahadır | R3 | planned |
| TC-009 | REQ-009 | I | Every (endpoint, role) pair of the matrix; request without token | Allowed → 2xx, forbidden → 403, no token → 401; only `/health` public | Bahadır | R3 | planned (UI role checks exist but are deliberately untagged, §4 rule 4) |
| TC-010 | REQ-010 | U, Inspection | Store "Test Patient" + HR 77; dump DB; tamper one ciphertext byte; search via blind index | No plaintext in the dump; round trip OK; tampering → decryption error; search works (PLN-05); no key in repo | Bahadır | R2 | pending (Bahadır's PR) |
| TC-011 | REQ-011 | I | Read/change data via API; try `UPDATE`/`DELETE` on audit table | One audit entry per request; UPDATE/DELETE rejected by the DB; readable by Auditor only | Bahadır | R3 | planned |
| TC-012 | REQ-012 | U, I | Trigger each hazard event type | Exactly one `HazardEvent` per trigger with UTC time, patient/device, type and the mapped RISK ID; readable by Doctor and Auditor only | Ege, Bahadır | R3 | planned (v0 data model in R2) |
| TC-013 | REQ-013 | I | Pair D1–P1; pair D1–P2; post from unpaired D9 | Readings stored for P1; second pairing → 4xx, unchanged; D9 → 4xx, not stored/forwarded, `UNPAIRED_DEVICE` (RISK-008) | Bahadır | R2 | pending (Bahadır's PR) |
| TC-014 | REQ-014 | U, I | Seed 30 h of readings incl. invalid ones; build chart data (R2: function; R3: via `GET /patients/{id}/readings`) | Exactly the valid readings in [now − 24 h, now], time order, HR/systolic/diastolic/SpO₂; invalid not plotted | Mert | R2 / R3 | **3 Vitest tests passing** (data part); API part R3 |
| TC-015 | REQ-015 | U | 4 vs 5 consecutive non-critical readings; normal reading in between; critical values; boundaries; per-vital counters | MEDIUM exactly at the 5th; reset by a normal value; no repeat; immediate HIGH for critical (RISK-009); systolic has no HIGH | Ege | R2 | 19 tests on Ege's branch |
| TC-016 | REQ-016 | U | SRS with untested Must REQ; JUnit with a failing test | `NO TEST`, `FAILING`; OK only with passing results; Markdown table written | Barış | R2 | 11 tests on Barış's branch |
| TC-017 | REQ-017 | U | SpO₂ 98 → 93 over 60 min vs 98 → 94 | One LOW trend alert vs none; threshold alarm priority unchanged | Ege | R4 (optional) | not started (optional) |
| TC-018 | REQ-018 | P | 20 patients × 1 Hz for 10 min; time from receipt to hand-over | p95 ≤ 200 ms | Bahadır, Mert | R4 | planned |
| TC-019 | REQ-019 | P (fault injection) | 1 h at 20 × 1 Hz with 10 % malformed/out-of-range input | 0 crashes; valid readings stored/forwarded; hazard events for out-of-range; 4xx for malformed | Bahadır, Mert | R4 | planned |
| TC-020 | REQ-020 | P (benchmark) | 10 000 writes + 10 000 reads with and without encryption on the CI runner | p95 difference ≤ 20 ms | Bahadır | R3 | planned |
| TC-021 | REQ-021 | – | *reserved* | – | – | – | – |
| TC-022 | REQ-022 | U (precondition), D | R2: automated click count from the patient list (banner) and from the alarm screen. R4: walkthrough with 5 Nurse-role users starting from the patient list | ≤ 2 clicks and ≤ 5 s per user | Mert | R2 / R4 | **2 Vitest tests passing** (click count); walkthrough R4 |
| TC-023 | REQ-023 | U, P | R2: 86 400 readings → downsampling keeps ≤ 1 000 points and each bucket's min/max; data preparation time. R4: 5 runs on a standard laptop (4 cores, 8 GB, Chrome), browser performance timing from opening the detail screen to the rendered chart | ≤ 1 000 points with bucket extremes kept; rendered ≤ 2 s in each of 5 runs | Mert | R2 / R4 | **2 Vitest tests passing**; preliminary browser timing below |
| TC-024 | REQ-024 | P (soak) | 8 h at 20 × 1 Hz; restart the backend with ≥ 3 active alarms incl. one unacknowledged HIGH | 0 crashes; same alarms (id, priority, state) after restart | Ege, Mert | R4 | planned |

**Preliminary REQ-023 evidence (not the formal TC-023 run):** the dashboard measures "open patient detail →
charts rendered" with the browser Performance API and shows it on screen. Measured on 14.11.2026 in headless
Chromium in a 4-vCPU cloud container: production build 257–415 ms (5 runs), dev server 579–728 ms (5 runs),
with 86 400 mock readings per vital. The formal run on a standard laptop is in R4.

## 6. Entry and exit criteria

| Sprint | Entry criteria | Exit criteria (gate) |
| --- | --- | --- |
| R2 (1–15 Nov) | SRS v2.0 draft, CI job `tests` exists | All R2 unit tests tagged and green in CI (`tests` and `frontend` jobs); JUnit artifact produced; test plan reviewed; **architecture frozen** |
| R3 (16–29 Nov) | Architecture frozen; R2 PRs merged; data contract unchanged | Integration tests for every Must REQ with an API part (TC-006 – TC-013 API parts, TC-007 API, TC-014 API) green; coverage targets of §3 met for ARC-002/003; no open `bug` issue of a safety-related REQ; **features frozen** |
| R4 (30 Nov–13 Dec) | Features frozen; Docker Compose stack runs | System, performance, soak, fault-injection and usability tests (TC-004, TC-018, TC-019, TC-022, TC-023, TC-024) executed and recorded; every Must REQ *OK* in the traceability matrix or a documented, risk-assessed exception; residual risk evaluation done → release v1.0 |

A PR may be merged only with green CI and the independent review (SDP §3, integrity level 3 for ARC-002/003).

## 7. Defect handling (IEC 62304 §9)

1. A failing test that is not fixed in the same PR, or any anomaly found during review/system test, is
   reported with the **Bug / anomaly** issue template (label `bug`).
2. The reporter states the affected REQ/TC; if the defect touches a risk control measure or could create a
   hazardous situation, the issue links the RISK ID in `docs/risk/risk-register.md` and gets label `risk`;
   Ege reviews the risk impact.
3. Fix on `fix/<issue-number>-<short-name>`; the PR adds a test that reproduces the defect, tagged with the
   affected `TC-xxx / REQ-xxx`, and closes the issue (`Closes #n`) only when that test passes in CI.
4. Process problems (tools, CI, schedule) are recorded in the members' report notes as `RSK-xx` items.

## 8. Test environment

| Item | Version / setting |
| --- | --- |
| CI runner | GitHub Actions `ubuntu-latest` |
| Python | 3.12 (CI and local `venv`), dependencies from `backend/requirements.txt` + `httpx` + `pytest-cov 7.1.0` |
| pytest config | `pytest.ini`: `testpaths = tests`, `pythonpath = backend`, `addopts = -q` |
| Node.js | 22 LTS (CI), dependencies from `frontend/package-lock.json` via `npm ci` |
| Frontend tests | Vitest 5.1 + jsdom + React Testing Library (`npm test -- --run`) |
| Test database | SQLite (unit/integration), PostgreSQL 16 in Docker Compose (system) |
| Test data | Simulated only (simulator, `frontend/src/mock/`); never real patient data |

**CI jobs** (`.github/workflows/ci.yml`):
- `tests`: `pytest --cov=backend/app --cov-branch --cov-report=term --junitxml=report.xml`; uploads
  `report.xml` as artifact **pytest-junit** (input of the Compliance Reporter, also when tests fail).
- `frontend`: `npm ci`, `npm test -- --run` (also writes `vitest-report.xml`, artifact **vitest-junit**),
  `npm run build`.

## 9. Test deliverables

- Test code in `tests/` and `frontend/src/**/*.test.ts(x)`; CI logs with coverage; JUnit artifacts.
- `docs/traceability.md` generated by the Compliance Reporter (after each sprint's merges).
- `docs/test/ui-wireframes.md` and `docs/test/screens/` (dashboard screens, PLN-06).
- R4: system/performance/soak/fault-injection results and the usability walkthrough record in `docs/test/`.

## 10. Change history

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | 2026-11-14 | Mert Eser | First version (PLN-07, Sprint 2). |

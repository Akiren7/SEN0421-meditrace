# MediTrace — Software Development Plan (SDP)

| Field | Value |
| --- | --- |
| Document ID | MT-SDP |
| Version | 1.0 |
| Date | 2026-11-14 |
| Author | Barış Bağbekleyen (Project & Standards Lead) |
| Standard | IEC 62304:2006+A1:2015 §5.1 (software development planning) |
| Related documents | `docs/SRS.md` (MT-SRS), `docs/risk/` (risk management plan and register), `docs/test/test-plan.md` (test plan), `docs/traceability.md` (generated) |

---

## 1. Purpose, scope and safety class

### 1.1 Purpose
This plan describes how the MediTrace team develops, verifies, configures and releases the MediTrace software so that the activities required by IEC 62304 for its safety class are carried out and documented. It is the reference for "how we work" during the four sprints of the course SEN0421 (Fall 2026).

### 1.2 Scope
MediTrace is a central (secondary) vital-sign monitoring and data management system for one general hospital ward, built with simulated device data only. The plan covers all software items ARC-001 – ARC-009 (simulator, backend components, dashboard and the Compliance Reporter CI tool). It does not cover real device integration, deployment in a hospital or maintenance after release.

### 1.3 Safety class and what it requires
MediTrace is **Class B** (IEC 62304 §4.3): its failure can contribute to a hazardous situation that results in non-serious injury, because the bedside monitors keep their own alarms and nurses perform rounds (external risk controls). If it became the primary alarm system or were used in an ICU it would be Class C.

| IEC 62304 clause | Required for Class B | How MediTrace applies it |
| --- | --- | --- |
| §4.3 Safety classification | Yes | Class B decision and assumption recorded (Progress Report 1, risk file) |
| §5.1 Development planning | Yes | This document |
| §5.2 Requirements analysis | Yes | `docs/SRS.md` v2.0 with acceptance criteria |
| §5.3 Architectural design | Yes | Architecture ARC-001 – ARC-009, SOUP list, data contract; frozen at the end of R2 |
| §5.4 Detailed design | §5.4.1 (units) yes; §5.4.2+ only Class C | Units identified for all items; **detailed design only for ARC-002 Ingestion & Validation and ARC-003 Alarm Engine** (team decision for safety-critical items) |
| §5.5 Unit implementation and verification | Yes | pytest / Vitest unit tests, PR review, coverage targets (§8) |
| §5.6 Integration and integration testing | Yes | API-level integration tests in CI (R3) |
| §5.7 System testing | Yes | Load, soak, fault-injection and usability tests (R4) |
| §5.8 Release | Yes | Release notes, known anomalies, tag `v1.0` (R4) |
| §7 Software risk management | Yes | ISO 14971 risk management plan and register (`docs/risk/`) |
| §8 Configuration management | Yes | Git/GitHub, protected `main`, pinned SOUP list (§6) |
| §9 Problem resolution | Yes | GitHub Issues with the "Bug / anomaly" template (§7) |
| §6 Maintenance | Tailored out | No deployment after the course; a maintenance plan is out of scope |
| QMS (ISO 13485) | Tailored | Replaced by lightweight QA: PR review, CI, issue templates |

---

## 2. Life cycle model

MediTrace uses an **incremental life cycle with four 2-week sprints**. Each sprint ends with a progress report to the instructor. IEC 62304 activities are distributed over the sprints; documents are living Markdown files under version control.

| Sprint / report | Dates (2026) | Main IEC 62304 activities | Content | Gate at end |
| --- | --- | --- | --- | --- |
| R1 Planning | 17 Oct – 31 Oct | §4.3, §5.1 (draft), §5.2 (draft), §7.1 | Scope, Class B, SRS draft (17 REQ), 10 risks, architecture draft — report submitted 31.10.2026 | – |
| R2 Requirements + skeleton | 1 Nov – 15 Nov | §5.1, §5.2, §5.3, §7, §8 | SRS v2.0, SDP, risk management plan, backend skeleton + simulator, alarm engine core, dashboard skeleton, test plan, CI, Compliance Reporter v0 | **Architecture frozen** |
| R3 Development | 16 Nov – 29 Nov | §5.4, §5.5, §5.6, §7.3 | Auth/RBAC (ARC-005), Audit Log (ARC-006), alarm engine wired into ingestion, WebSocket push, dashboard on the real API, complete hazard log, alarm acknowledgement, escalation decision | **Features frozen** |
| R4 Verification + release | 30 Nov – 13 Dec | §5.7, §5.8, §7.4 | System, load and soak tests, usability walkthrough, compliance PDF, residual risk evaluation, release notes, demo | **Release `v1.0`** |

Gate rules:
- **Architecture frozen (end of R2):** after this gate, a change of a component, interface or the shared data contract needs a GitHub issue labelled `requirement` and agreement of the whole team in the weekly meeting.
- **Features frozen (end of R3):** after this gate only defect fixes, tests and documentation are merged.
- Work for a later sprint is not built early; a clearly marked hook (comment or stub) is left instead.

---

## 3. Roles and responsibilities

| Member | Role | Responsibilities |
| --- | --- | --- |
| Barış Bağbekleyen | Project & Standards Lead | Plan and schedule, SRS (§5.2), SDP (§5.1), traceability and Compliance Reporter (ARC-009), configuration management (repository, ruleset, tags), compiling progress reports |
| Ege Arıcan | Risk Management Lead | ISO 14971 risk management plan and register, risk control measures, Alarm Engine (ARC-003), residual risk evaluation |
| Bahadır Duran | Backend & Security Developer | Backend skeleton and simulator (ARC-001, ARC-002, ARC-004, ARC-007), security (ARC-005, ARC-006, encryption, blind index), SOUP list in `backend/requirements.txt` |
| Mert Eser | Frontend & Test Lead | Dashboard (ARC-008), test plan, CI configuration, test tooling (`pytest.ini`, Vitest) |
| All | – | PR reviews, SOUP version pinning, architecture review, weekly meeting, own report notes |

Independent review pairs (IEEE 1012): Barış reviews Bahadır · Bahadır reviews Ege · Ege reviews Mert · Mert reviews Barış.

---

## 4. Deliverables per IEC 62304 activity

| Activity (IEC 62304) | Document / artefact | Location | Owner | Sprint |
| --- | --- | --- | --- | --- |
| §4.3 Safety classification | Class B decision, assumptions | Progress Report 1, `docs/risk/` | Barış, Ege | R1 |
| §5.1 Development planning | Software Development Plan | `docs/SDP.md` | Barış | R2 |
| §5.2 Requirements analysis | Software Requirements Specification v2.0 | `docs/SRS.md` | Barış | R2 |
| §5.3 Architectural design | Architecture (ARC list, data contract, SOUP) | Progress Report 1 Annex, `docs/` | All (review), Bahadır (SOUP) | R1–R2 |
| §5.4 Detailed design | Detailed design of ARC-002 and ARC-003 | `docs/` | Bahadır, Ege | R3 |
| §5.5 Unit implementation and verification | Source code, unit tests, review records (PRs) | `backend/`, `simulator/`, `frontend/`, `tests/` | All | R2–R3 |
| §5.6 Integration testing | API integration tests, CI results | `tests/`, GitHub Actions | Mert, Bahadır | R3 |
| §5.7 System testing | Test plan, load / soak / fault-injection / usability results | `docs/test/` | Mert | R2 (plan), R4 |
| §5.8 Release | Release notes, known anomalies, tag `v1.0` | `docs/`, Git tag | Barış | R4 |
| §7 Risk management | Risk management plan, risk register, hazard log data, residual risk | `docs/risk/` | Ege | R1–R4 |
| §7.3.3 Traceability | Generated traceability matrix | `docs/traceability.md` (Compliance Reporter) | Barış | R2–R4 |
| §8 Configuration management | Repository, ruleset, SOUP list, tags | GitHub, `backend/requirements.txt` | Barış, Bahadır | R1–R4 |
| §9 Problem resolution | Bug / anomaly issues, verifying tests | GitHub Issues | All | R2–R4 |
| Progress reports | Reports 1–4 compiled from member notes | `docs/reports/` | Barış (compiles), all (notes) | each sprint |

---

## 5. Standards, methods and tools

| Standard | Use |
| --- | --- |
| IEC 62304:2006+A1:2015 | Software life cycle processes (main standard) |
| ISO 14971:2019 | Risk management: hazards, S × P estimation, controls, residual risk |
| IEC 60601-1-8 | Alarm priorities and acknowledgement behaviour |
| IEEE 29148 | Requirement quality and SRS structure |
| IEEE 1016 | Software design description and viewpoints |
| ISO/IEC 25010 | Quality characteristics used for non-functional requirements (performance, reliability, usability, security) |
| IEEE 1012 | Verification & validation, integrity levels |
| ISO/IEC 12207 | Life cycle processes that IEC 62304 maps onto |
| KVKK (Law 6698) | Health data is special-category personal data: encryption, access control, access logging |

| Tool / technology | Use |
| --- | --- |
| Python 3.12, FastAPI | Backend, simulator, Compliance Reporter |
| PostgreSQL 16 (SQLite in tests) | Database behind the Encrypted Data Layer |
| React + TypeScript (Vite), Vitest | Monitoring dashboard and its tests |
| pytest | Unit and integration tests |
| Git, GitHub (Issues, Pull Requests, rulesets) | Version control, review, problem resolution |
| GitHub Actions | Continuous integration (`tests` job) |
| Docker Compose | Local start of backend, database and dashboard |

---

## 6. Configuration management (IEC 62304 §8)

1. **Configuration items:** all source code, tests, documents in `docs/`, CI workflows, issue templates and the SOUP list are kept in the Git repository `Akiren7/SEN0421-meditrace`. Progress reports are stored in `docs/reports/`.
2. **Branching:** `main` holds the integrated, reviewed state. Work is done on short-lived branches `feature/<PLN-id or REQ-id>-<short-name>` or `fix/<issue-number>-<short-name>`. Nobody commits to `main` directly.
3. **Ruleset `protect-main`:** changes reach `main` only through a pull request with **at least 1 approval**; force pushes and branch deletion are blocked. (Introduced after RSK-09: before the ruleset a direct push to `main` was possible; the rule was verified by a rejected test push, error GH013.)
4. **Merge method:** "Create a merge commit" (no squash), so that individual `REQ-xxx:` commits remain visible in the history.
5. **Commit and ID conventions:** commit messages start with the traced ID (`REQ-015: …`, `PLN-02: …`) or with `docs:`, `test:`, `chore:`. Each member commits with their own Git identity. IDs (REQ, RISK, RCM, ARC, TC, RSK, PLN) are never renumbered. Traceability tags in code and tests: `# Implements REQ-xxx`, `# Controls RISK-xxx`, test docstring / test name `TC-xxx / REQ-xxx: …`.
6. **SOUP (§8.1.2):** every third-party package is listed with a pinned version in `backend/requirements.txt` (pinned in Sprint 2, PLN-08); frontend packages are pinned by `frontend/package-lock.json`. A new SOUP item is added only via a PR that names it in the description; only the backend owner edits `backend/requirements.txt`.
7. **Release identification:** Git tags `v0.x` at the end of each sprint (`v0.2` end of R2, `v0.3` end of R3) and `v1.0` for the release in R4. The generated `docs/traceability.md` is regenerated before every tag.
8. **Secrets:** no real keys, passwords or patient data are committed. Configuration secrets come from environment variables (`.env` is git-ignored).

---

## 7. Problem resolution (IEC 62304 §9)

1. Every defect or anomaly found in review, testing, CI or use is reported as a **GitHub issue** with the **"Bug / anomaly"** template and the label `bug` (other labels: `requirement`, `risk`, `docs`).
2. The issue records: observed vs expected behaviour, steps to reproduce, affected REQ / ARC IDs and version (commit or tag).
3. **Analysis against the risk file:** the owner checks whether the defect affects a risk control measure or creates a new hazardous situation. If yes, the risk register is updated (new or changed RISK / RCM, label `risk`) and Ege (Risk Management Lead) reviews the change.
4. **Fix:** on a `fix/<issue-number>-<short-name>` branch; the PR references the issue (`Closes #n`).
5. **Verification before closing:** an issue is closed only after a **test that reproduces the defect** has been added (tagged with the affected `TC-xxx / REQ-xxx`), passes in CI and the PR has been reviewed and merged.
6. Problems in the process itself (tools, schedule, team) are recorded as `RSK-xx` items in the members' report notes and summarised in each progress report.

---

## 8. Verification strategy

The detailed test plan is maintained by the Frontend & Test Lead in **`docs/test/test-plan.md`** (PLN-07). Summary:

- **Levels:** unit tests (pytest, Vitest) → API integration tests → system tests (load, soak, fault injection, usability walkthrough).
- **Naming:** test case TC-xxx verifies REQ-xxx with the same number; every test carries the `TC-xxx / REQ-xxx` tag so the Compliance Reporter can trace it.
- **Continuous integration:** the GitHub Actions job `tests` runs `pytest -q` on every pull request and on `main`; a PR is merged only with a green CI.
- **Reviews:** every PR is reviewed by the assigned independent reviewer (§3), who checks CI, tags, file scope and the notes file and leaves at least one real comment.
- **Integrity levels (IEEE 1012, team decision):**

| Integrity level | Components | Required verification |
| --- | --- | --- |
| 3 | ARC-002 Ingestion & Validation, ARC-003 Alarm Engine | Every change needs an **independent PR review** (reviewer not the author); **branch coverage ≥ 80 %**; detailed design (§5.4) |
| 2 | All other components (ARC-001, ARC-004 – ARC-009) | PR review; **line coverage ≥ 60 %** |

- **Traceability evidence:** `docs/traceability.md`, generated from the SRS, the code tags, the tests and the CI JUnit result. A requirement counts as verified only if its tests passed in a real test run (RCM-010).

---

## 9. Risk management link

Software risk management (IEC 62304 §7) follows ISO 14971 and is owned by the Risk Management Lead. The risk management plan and the risk register are in **`docs/risk/`** (`risk-management-plan.md`, `risk-register.md`). Links to this plan:
- each risk control measure that is implemented in software becomes a requirement in the SRS (Related risks row) and is verified by a TC;
- defects are analysed against the risk register before they are closed (§7);
- the hazard log (ARC-004, REQ-012) provides data to update the probability estimates (RSK-03);
- residual risk is evaluated in R4 before release.

---

## 10. Change log of this plan

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | 2026-11-14 | Barış Bağbekleyen | First version (PLN-02, Sprint 2). |

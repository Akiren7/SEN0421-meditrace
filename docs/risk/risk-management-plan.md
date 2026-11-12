# MediTrace — Risk Management Plan (ISO 14971:2019 §4.4)

| Item | Value |
| --- | --- |
| Document | Risk management plan, part of the risk management file (`docs/risk/`) |
| Version | 1.0 (Sprint 2, PLN-03) |
| Owner | Ege Arıcan, Risk Management Lead |
| Reviewer | Barış Bağbekleyen, Project & Standards Lead |
| Related | [`risk-register.md`](risk-register.md) (risks, risk control measures, decisions), SRS (`docs/SRS.md`, PLN-01), SDP (PLN-02), test plan (`docs/test/test-plan.md`, PLN-07) |
| Standards | ISO 14971:2019, IEC 62304:2006+A1:2015 §4.3 and §7, IEC 60601-1-8 (alarm priorities) |

> Educational project: MediTrace only processes simulated data. Nothing in the risk management file is clinical advice.

The table below shows where this plan covers each element ISO 14971 §4.4 requires.

| §4.4 | Required content | Section |
| --- | --- | --- |
| a | Scope, device description, life-cycle phases | [1](#1-scope) |
| b | Responsibilities and authorities | [2](#2-responsibilities-and-authorities) |
| c | Review of risk management activities | [3](#3-reviews) |
| d | Risk acceptability criteria, incl. when probability cannot be estimated | [4](#4-risk-acceptability-criteria), [5](#5-software-failures-and-probability-estimation) |
| e | Method and criteria for overall residual risk | [7](#7-overall-residual-risk) |
| f | Verification of implementation and effectiveness of risk control measures | [6](#6-verification-of-risk-control-measures) |
| g | Production and post-production information | [8](#8-production-and-post-production-information) |

## 1. Scope

**Device.** MediTrace is a central vital-sign monitoring and data management system for one **general hospital ward**. It collects heart rate (HR), systolic and diastolic blood pressure and SpO₂ once per second per patient from (simulated) bedside devices, validates the readings, stores them encrypted, raises prioritized smart alarms and logs hazardous events. Components ARC-001 … ARC-009 are listed in the architecture (A6 of the project context and `docs/README.md`).

**Intended use.** A **secondary (central) monitor**. Bedside monitors keep their own alarms and nurses do periodic rounds. These two **external risk control measures** are the reason for software safety **Class B** (IEC 62304 §4.3). Users are Doctor, Nurse, Admin and Auditor.

**Reasonably foreseeable misuse (ISO 14971 §5.2).**

| Misuse | Effect on the risk file |
| --- | --- |
| Used as the primary alarm system, or in an ICU | External controls no longer apply: probabilities in the register become invalid and the software would be Class C. The release notes (R4) will state the intended use as information for safety. |
| Bedside monitor alarms switched off because "the central station alarms" | Same as above. This is covered by the same information for safety. |
| Shared login between nurses | Breaks audit attribution (RISK-006 / RISK-007). This is covered by RCM-006 and the audit log (REQ-011). |
| Thresholds widened to silence nuisance alarms | Covered by RISK-004: only a Doctor can change thresholds, and every change is audited. ARC-003 also rejects inconsistent settings (e.g. a critical limit inside the non-critical band), but it cannot detect a deliberately wide setting. |

**Life-cycle phases covered.** Planning, requirements, architecture, implementation, verification and release, in Sprints R1–R4 (17 Oct – 13 Dec 2026). Maintenance (IEC 62304 §6) is tailored out because there is no deployment. Post-production activities are reduced to the sources in §8.

**Out of scope for this risk file.** Real device hardware, HL7/FHIR interfaces, diagnosis or treatment advice, and the mobile app are not analysed. All of them are out of the product scope. The bedside monitors are treated as external systems.

## 2. Responsibilities and authorities

| Role | Member | Responsibility in risk management |
| --- | --- | --- |
| Risk Management Lead | Ege Arıcan | Owns this plan and the risk register. Identifies hazards, estimates and evaluates risks, and proposes and decides risk control measures (RCMs). Leads the sprint risk reviews. Implements the Alarm Engine (ARC-003) RCMs. |
| Project & Standards Lead | Barış Bağbekleyen | Reviews and approves the risk documents. Ensures every RCM is a requirement in the SRS. Owns the compliance reporter (RCM-010). Signs off the final risk management review (§3). |
| Backend & Security Developer | Bahadır Duran | Implements the RCMs in ARC-002, ARC-005, ARC-006 and ARC-007 (plausibility, pairing, RBAC, audit, encryption). Reports new hazards found in the backend. |
| Frontend & Test Lead | Mert Eser | Implements the alarm presentation (ARC-008, REQ-005), owns the test plan and verifies the RCMs through tests. |
| All members | – | Report hazards and anomalies as GitHub Issues (label `risk`, or the *Bug / anomaly* template, IEC 62304 §9). Review the architecture and the register at each sprint gate. |

**Competence (ISO 14971 §4.3).** This is a student team. Competence comes from the course (SEN0421), official standard previews and summaries (full texts are not available, RSK-01) and peer review of every risk document.

## 3. Reviews

| Review | When | Who | Record |
| --- | --- | --- | --- |
| Pull request review of any change in `docs/risk/` or of RCM code | Every PR | An independent reviewer (A10) checks the IDs, the RCM → REQ → TC traceability and that the `# Controls RISK-xxx` annotations exist | GitHub PR |
| Sprint risk review | End of R2, R3, R4 | All members, led by the Risk Management Lead | Progress report and the change log in the risk register |
| Risk management review (ISO 14971 §9) | Before the `v1.0` release (R4) | Risk Management Lead, approved by the Project & Standards Lead | Risk management report in `docs/risk/` |

## 4. Risk acceptability criteria

### 4.1 Severity (S)

| S | Name | Definition |
| --- | --- | --- |
| 1 | Negligible | Inconvenience, no harm |
| 2 | Minor | Temporary harm, no medical intervention needed |
| 3 | Moderate | Temporary harm that needs medical intervention |
| 4 | Serious | Permanent harm or life-threatening |
| 5 | Catastrophic | Death |

Severity is estimated for the worst credible case, without credit for external risk controls.

### 4.2 Probability (P)

| P | Name | Definition |
| --- | --- | --- |
| 1 | Very low | Not expected during the system's life |
| 2 | Low | Rarely |
| 3 | Medium | Occasionally |
| 4 | High | Frequently |
| 5 | Very high | Almost every use |

P is the probability that the **hazardous situation leads to harm** (see §5 for software).

### 4.3 Risk matrix (score = S × P)

| S \ P | 1 Very low | 2 Low | 3 Medium | 4 High | 5 Very high |
| --- | --- | --- | --- | --- | --- |
| **5 Catastrophic** | 5 ALARP | 10 **U** | 15 **U** | 20 **U** | 25 **U** |
| **4 Serious** | 4 A | 8 ALARP | 12 **U** | 16 **U** | 20 **U** |
| **3 Moderate** | 3 A | 6 ALARP | 9 ALARP | 12 **U** | 15 **U** |
| **2 Minor** | 2 A | 4 A | 6 ALARP | 8 ALARP | 10 **U** |
| **1 Negligible** | 1 A | 2 A | 3 A | 4 A | 5 ALARP |

A = acceptable, ALARP = as low as reasonably practicable, **U** = unacceptable.

| Score | Region | Decision rule |
| --- | --- | --- |
| 1–4 | **Acceptable** | No further reduction is required. Existing RCMs are still verified. |
| 5–9 | **ALARP** | The risk must be reduced as far as practicable. A residual ALARP risk is accepted only with a documented justification: the measures considered, why further measures are not practicable, and the benefit. |
| 10–25 | **Unacceptable** | The risk must be reduced. The software is not released while any residual risk is in this region. |

## 5. Software failures and probability estimation

IEC 62304 assumes that software can fail, and the probability of a software failure cannot be estimated meaningfully (RSK-03). MediTrace therefore uses this method:

1. **Assume the software fails.** The probability of the software failure itself is taken as 1.
2. **Estimate P as the probability that the resulting hazardous situation leads to harm.** This takes into account the external controls (bedside monitor alarms, nursing rounds) and the design of the system (e.g. other channels still alarming).
3. **When P cannot be estimated with confidence,** the risk is evaluated on severity first. Any hazard with **S ≥ 4 must have at least one RCM** regardless of the estimated P, and the RCM must be verified by a test.
4. **Update estimates with data.** The Hazard Log (ARC-004) records every hazardous event with its RISK ID. In R3 and R4 the event counts from the simulator fault scenarios and the soak test (TC-024) are used to review the P values. Every change is recorded in the register's change log.
5. **Software items that contribute to hazardous situations** (IEC 62304 §7.1) are ARC-002 Ingestion & Validation and ARC-003 Alarm Engine. They get IEEE 1012 integrity level 3: an independent PR review for every change and branch coverage ≥ 80 %.
6. **SOUP** (IEC 62304 §7.1.2–7.1.3) is part of the analysis. After the versions are pinned (PLN-08), the published anomaly lists of FastAPI, `cryptography` and `argon2-cffi` are reviewed in R3.

## 6. Verification of risk control measures

- **Traceability.** Every RCM traces to at least one **REQ** and one **TC**, and is listed in the RCM table of the register. An RCM without a TC is shown as not verified.
- **Implementation** (ISO 14971 §7.2) is verified by code review. The implementing code carries `# Implements REQ-xxx` and `# Controls RISK-xxx` annotations.
- **Effectiveness** is verified by the TC tagged with the RCM's REQ (`TC-xxx / REQ-xxx` on the first docstring line, A8). An RCM counts as **verified only when its TC passes in CI on `main`**. The compliance reporter (ARC-009) reads real CI results (RCM-010).
- **New risks from RCMs** (ISO 14971 §7.5) are checked for every new or changed RCM and recorded in the register. RISK-009 is an example: it was created by the smart validation of RCM-005.
- **Status vocabulary** used in the register:

| Status | Meaning |
| --- | --- |
| Planned (Rx) | RCM decided, implementation scheduled for sprint Rx |
| In progress | Being implemented in the current sprint |
| Implemented – unit verified | Code merged or in review, and unit TC passing |
| Verified | All TCs of the RCM pass in CI, including integration and system level |
| Accepted residual | Residual risk evaluated and accepted (R4) |

## 7. Overall residual risk

The overall residual risk is evaluated in **R4** (ISO 14971 §8) with the following method:

1. Review all individual residual risks together, including **combinations** that individual rows miss. Examples: smart validation plus the artefact check delaying the same alarm (RISK-009 with RCM-002b), alarm fatigue across 20 patients (RISK-005), and data loss during an active alarm (RISK-001 with RISK-005).
2. Check completeness of risk control (§7.6): every hazard in the register has been analysed, controlled and verified.
3. Do a benefit-risk analysis (§7.4) for every residual risk left in the ALARP region.

**Acceptance criteria for the overall residual risk:**

- no individual residual risk is in the unacceptable region;
- every ALARP residual risk has a documented justification;
- every RCM has the status *Verified* in the compliance report generated from CI;
- for the intended use as a secondary monitor, the benefits (central overview, earlier recognition of deterioration, data retention, access logging) outweigh the residual risk.

The result is written to the risk management report and summarized in the Progress Report 4 and the release notes.

## 8. Production and post-production information

There is no clinical deployment, so ISO 14971 §10 is tailored. The sources of "field" information are:

- **Hazard Log** events (ARC-004) from simulator fault scenarios, load and soak tests;
- **GitHub Issues** labelled `risk` or `bug` (IEC 62304 §9 problem resolution);
- **CI test failures** on RCM tests.

Each item is reviewed in the sprint risk review. If it reveals a new hazard or a wrong estimate, the register is updated within the same sprint. Every software change that touches an RCM gets a risk analysis of the change (IEC 62304 §7.4) in its PR description.

## 9. Risk management file (ISO 14971 §4.5)

| Content | Location |
| --- | --- |
| Risk management plan | `docs/risk/risk-management-plan.md` (this file) |
| Risk analysis, evaluation, control and residual risk (register, RCM table, decisions) | `docs/risk/risk-register.md` |
| Initial risk analysis (R1) | `docs/reports/SDS-02_Progress_Report_1_MediTrace.docx`, Annex C |
| RCM requirements | SRS (`docs/SRS.md`) |
| RCM implementation | Source code with `# Controls RISK-xxx` annotations, e.g. `backend/app/alarm/` |
| Verification evidence | Tests (`tests/`), CI results, generated traceability matrix (`docs/traceability.md`) |
| Risk management report | `docs/risk/` (R4) |

## 10. Risk management activities per sprint

| Sprint | Risk management activities | Output | Gate |
| --- | --- | --- | --- |
| R1 Planning (17–31 Oct) | Intended use, hazard identification, S/P scales and 5×5 matrix, 10 risks with initial RCMs, risk created by a control (RISK-009) | Progress Report 1, Annex C | – |
| **R2 Requirements + skeleton (1–15 Nov)** | This plan. Register moved to the repository. RCM-002b evaluated and implemented. RCM-005b decision. Threshold rationale with literature check. Alarm Engine core with RCM-001, RCM-002b, RCM-005 (smart validation, priorities) and RCM-009, unit-tested (TC-002, TC-003, TC-015). | `docs/risk/*`, `backend/app/alarm/`, `tests/test_alarm_engine.py` | Architecture frozen |
| R3 Development (16–29 Nov) | Implement and verify the remaining RCMs: RCM-003 (WebSocket push), RCM-004, RCM-005 acknowledgement, RCM-005b escalation, RCM-006, RCM-007 audit. Hazard Log complete with RISK IDs. First P review with Hazard Log data. Risk analysis of changes. SOUP anomaly review. | Updated register, RCM tests in CI | Features frozen |
| R4 Verification + release (30 Nov–13 Dec) | System, load and soak tests for RCMs (TC-004, TC-024). Residual risk evaluation per risk (§7.3). Benefit-risk for ALARP residuals (§7.4). Completeness (§7.6). Overall residual risk (§8). Risk management review (§9). | Risk management report, final register | Release `v1.0` |

## 11. Change history

| Version | Date | Author | Change |
| --- | --- | --- | --- |
| 1.0 | 2026-11-12 | Ege Arıcan | First version (PLN-03) |

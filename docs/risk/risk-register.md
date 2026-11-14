# MediTrace — Risk Register (ISO 14971:2019 §5–7)

| Item | Value |
| --- | --- |
| Version | 2.0 (Sprint 2, PLN-03). Version 1 was Progress Report 1, Annex C. |
| Owner / reviewer | Ege Arıcan (Risk Management Lead) / Barış Bağbekleyen (Project & Standards Lead) |
| Criteria | S, P, regions and status vocabulary are defined in [`risk-management-plan.md`](risk-management-plan.md) §4–6 |
| Status date | 2026-11-12 |

IDs are never renumbered. New items continue from the last number. RCM-002b and RCM-005b are refinements of RCM-002 and RCM-005.

## 1. Register

*Residual* values are the **estimates after risk control**. They become final only after the RCMs are verified and the residual risk is evaluated in R4 (plan §7). Regions: A = acceptable, ALARP, U = unacceptable.

| Risk ID | Hazardous situation | Harm | S | P | Score | Region | Control measure (RCM) | REQ | TC | Residual S × P | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RISK-001 | Device or network drop goes unnoticed | Deterioration noticed late | 4 | 3 | 12 | U | RCM-001 data-loss technical alarm (HIGH) after 10 s | REQ-003, REQ-024 | TC-003, TC-024 | 4×1 = 4 (A) | RCM-001 implemented – unit verified in ARC-003 (TC-003, R2). Wiring to ingestion and a 1 Hz scheduler in R3. Soak/restart TC-024 in R4. |
| RISK-002 | Artefact or faulty reading enters the system | False alarm, or a real alarm masked | 3 | 4 | 12 | U | RCM-002 plausibility range check; **RCM-002b rate-of-change artefact check (new, R2)** | REQ-002, REQ-019 | TC-002, TC-019 | 3×2 = 6 (ALARP) | RCM-002 in progress in ARC-002 (PLN-04). RCM-002b implemented – unit verified in ARC-003 (TC-002 engine part, R2). Residual P unchanged, see §3.1. |
| RISK-003 | Alarm reaches the dashboard late | Delayed intervention | 4 | 2 | 8 | ALARP | RCM-003 3 s deadline after validation, audible HIGH alarm, WebSocket push | REQ-004, REQ-005, REQ-018, REQ-020 | TC-004, TC-005, TC-018, TC-020 | 4×1 = 4 (A) | Planned (R3: WebSocket push, alarm banner and sound; R4: load test TC-004). Priorities already assigned by ARC-003 (R2). |
| RISK-004 | Unauthorized user changes a threshold | Alarm silenced | 4 | 2 | 8 | ALARP | RCM-004 threshold change Doctor-only, every change audited | REQ-006 | TC-006 | 4×1 = 4 (A) | Planned (R3, ARC-005/ARC-006). ARC-003 provides per-patient thresholds and rejects inconsistent ones, but does not claim REQ-006. |
| RISK-005 | Alarm closes unnoticed, or alarm fatigue | Critical condition missed | 3 | 3 | 9 | ALARP | RCM-005 acknowledgement required, three priorities, smart validation; **RCM-005b escalation of an unacknowledged HIGH alarm after 60 s (accepted for R3)** | REQ-005, REQ-007, REQ-015, REQ-022, REQ-024 | TC-005, TC-007, TC-015, TC-022, TC-024 | 3×2 = 6 (ALARP); target 3×1 = 3 (A) when RCM-005b is verified | Smart validation and priorities implemented – unit verified (TC-015, R2). Acknowledgement and RCM-005b planned (R3), see §3.2. |
| RISK-006 | Unauthorized access (password guessing, out-of-role API call) | Misuse of data or settings | 3 | 3 | 9 | ALARP | RCM-006 Argon2 hashing, lockout after 5 failures, per-endpoint RBAC | REQ-008, REQ-009 | TC-008, TC-009 | 3×1 = 3 (A) | Planned (R3, ARC-005). |
| RISK-007 | Health-data leak after a database compromise | Privacy breach (KVKK) | 3 | 2 | 6 | ALARP | RCM-007 AES-256-GCM field encryption, append-only audit log | REQ-010, REQ-011 | TC-010, TC-011 | 3×1 = 3 (A) | Encrypted data layer in progress (ARC-007, PLN-04/05). Audit log planned (R3, ARC-006). |
| RISK-008 | Reading attached to the wrong patient | Wrong-patient intervention | 4 | 2 | 8 | ALARP | RCM-008 1:1 device–patient pairing, unpaired data rejected and hazard-logged | REQ-013 | TC-013 | 4×1 = 4 (A) | In progress (ARC-002, PLN-04). |
| RISK-009 | Smart validation delays the alarm in a real deterioration (risk created by RCM-005, ISO 14971 §7.5) | Delayed intervention | 4 | 2 | 8 | ALARP | RCM-009 validation window limited to 5 readings (5 s), critical values bypass it | REQ-015 | TC-015 | 4×1 = 4 (A) | Implemented – unit verified (TC-015, R2). Re-evaluated for RCM-002b: worst-case MEDIUM delay grows by one reading, and critical values are never suppressed. S and P unchanged (§3.1). |
| RISK-010 | Compliance report shows an untested REQ as satisfied | Unverified safety measure released | 3 | 2 | 6 | ALARP | RCM-010 report built only from real CI results, missing or failing tests flagged | REQ-016 | TC-016 | 3×1 = 3 (A) | In progress (ARC-009, Barış). See open point 5 on partially verifying tests. |

**Summary.** Before control: 2 unacceptable, 8 ALARP. After control (estimated): 8 acceptable, 2 ALARP (RISK-002 and RISK-005), 0 unacceptable.

### 1.1 Risk matrix positions

Before control:

| S \ P | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| **5** | | | | | |
| **4** | | RISK-003, RISK-004, RISK-008, RISK-009 | RISK-001 | | |
| **3** | | RISK-007, RISK-010 | RISK-005, RISK-006 | RISK-002 | |
| **2** | | | | | |
| **1** | | | | | |

After control (estimated residual):

| S \ P | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| **5** | | | | | |
| **4** | RISK-001, RISK-003, RISK-004, RISK-008, RISK-009 | | | | |
| **3** | RISK-006, RISK-007, RISK-010 | RISK-002, RISK-005 | | | |
| **2** | | | | | |
| **1** | | | | | |

## 2. Risk control measures

ISO 14971 §7.1 lists three control options in priority order: inherent safety by design, protective measures, and information for safety. The **external** controls (bedside monitor alarms and nursing rounds) are outside the software. They are the basis of Class B and are communicated as information for safety in the release notes (R4).

| RCM | Measure | Option (§7.1) | Risk | REQ | ARC | TC | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RCM-001 | DATA_LOSS HIGH technical alarm when `now − last reading ≥ 10 s`, raised once per silence | Protective | RISK-001 | REQ-003 | ARC-003 | TC-003 | Implemented – unit verified (R2) |
| RCM-002 | Plausibility range check (HR 20–300, SpO₂ 50–100, sys 40–300, dia 20–200, sys > dia). Invalid readings excluded and hazard-logged. | Protective | RISK-002 | REQ-002 | ARC-002 | TC-002 | In progress (R2, PLN-04) |
| **RCM-002b** | Rate-of-change check. A suspected artefact is not counted in the confirmation window and produces a LOW ARTEFACT_SUSPECTED event (§3.1). | Protective | RISK-002 | REQ-002 | ARC-003 | TC-002 | Implemented – unit verified (R2) |
| RCM-003 | 3 s alarm deadline after validation, WebSocket push (not polling), audible HIGH alarm | Inherent by design (push) + protective | RISK-003 | REQ-004, REQ-005 | ARC-003, ARC-008 | TC-004, TC-005 | Planned (R3/R4) |
| RCM-004 | Thresholds changeable only by Doctor, every change audited | Protective | RISK-004 | REQ-006 | ARC-005, ARC-006 | TC-006 | Planned (R3) |
| RCM-005 | HIGH alarm stays until acknowledged, three priorities, smart validation | Protective | RISK-005 | REQ-005, REQ-007, REQ-015 | ARC-003, ARC-008 | TC-005, TC-007, TC-015 | Priorities and smart validation implemented – unit verified (R2). Acknowledgement planned (R3). |
| **RCM-005b** | Re-alert of a HIGH alarm still unacknowledged after 60 s (§3.2) | Protective | RISK-005 | New REQ, to be numbered by the Project & Standards Lead in the SRS | ARC-003, ARC-008 | New TC (same number as the REQ) | Planned (R3) |
| RCM-006 | Argon2 hashing, 15 min lockout after 5 failures, RBAC on every endpoint | Protective | RISK-006 | REQ-008, REQ-009 | ARC-005 | TC-008, TC-009 | Planned (R3) |
| RCM-007 | AES-256-GCM field encryption, only ARC-007 writes to the DB, append-only audit log | Inherent by design + protective | RISK-007 | REQ-010, REQ-011 | ARC-006, ARC-007 | TC-010, TC-011 | In progress (R2) / planned (R3) |
| RCM-008 | One device ↔ one patient, unpaired data rejected and hazard-logged | Protective | RISK-008 | REQ-013 | ARC-002 | TC-013 | In progress (R2, PLN-04) |
| RCM-009 | Confirmation window limited to 5 readings, critical values bypass it | Inherent by design | RISK-009 | REQ-015 | ARC-003 | TC-015 | Implemented – unit verified (R2) |
| RCM-010 | Compliance report only from real CI results, missing or failing tests flagged | Protective | RISK-010 | REQ-016 | ARC-009 | TC-016 | In progress (R2) |

## 3. PLN-03 risk work in Sprint 2

### 3.1 RCM-002b — rate-of-change artefact check (RISK-002)

**Why.** RCM-002 only removes values outside physiological ranges. Typical artefacts (probe slipping off, patient movement, ECG lead problems) often produce values that are **inside** those ranges and pass REQ-002. Such readings can start or feed the 5-reading confirmation window, or cause false alarms that add to alarm fatigue (RISK-005). After RCM-002, RISK-002 stays at ALARP (3×2 = 6), so ISO 14971 §7.1 requires checking whether a further practicable measure exists.

**Decision.** Accepted and implemented in Sprint 2 in the Alarm Engine (`AlarmEngine._is_suspected_artefact`, `ArtefactLimits` in `backend/app/alarm/`).

**Chosen limits** (between two consecutive readings at most 2 s apart; strict `>` like the threshold boundary rule):

| Vital | Suspected artefact when | Rationale |
| --- | --- | --- |
| HR | change of **more than 60 bpm** in either direction | Monitors report HR averaged over several beats, so a step of more than 60 bpm from one 1 Hz value to the next is far more often lead-off, motion or a counting error than physiology. A real abrupt onset (e.g. a tachyarrhythmia) that lands in the critical range still alarms immediately (decision 1 below). |
| SpO₂ | **drop of more than 15 points** | Pulse oximeters average over several seconds, and even in apnoea a real desaturation takes many seconds. A fall of more than 15 points within 1 s is typical of probe displacement. A fast **rise** is not checked: it cannot cause a false low-SpO₂ alarm, and it usually means the probe was reattached. |
| Systolic / diastolic BP | no rule in v1 | BP artefacts are handled by RCM-002 and by having no critical bypass for BP: a single outlier is absorbed by the 5-reading confirmation. To be revisited with simulator data in R3. |

**Design decisions:**

1. **The critical bypass wins.** A reading that is both a suspected artefact and critical still raises the HIGH alarm immediately, and the LOW artefact event is emitted next to it. Suppressing it would create a new risk of masking a real deterioration (ISO 14971 §7.5, same reasoning as RISK-009).
2. **The comparison is always with the immediately previous reading,** even if that reading was itself flagged. Comparing with the last *accepted* reading was considered and rejected: a real step change that persists (e.g. HR 75 → 140 and staying) would then be flagged on every reading, and the MEDIUM alarm would never be raised. With the chosen rule a step is flagged once and counts from the next reading. Worst case, the MEDIUM alarm comes after 6 readings instead of 5.
3. **A suspected artefact neither counts nor resets.** It cannot add to the confirmation window, and it cannot end a running window or an active alarm episode. This is the conservative choice.
4. **No check without a usable reference.** For the first reading of a patient, the first reading after a gap of more than 2 s (e.g. after data loss), or a reading that is not newer than the previous one, no artefact check is done. The limits are defined per second.
5. Every flagged reading produces an `ARTEFACT_SUSPECTED` / `LOW` event with `risk_id = RISK-002`. From Sprint 3 it is also written to the Hazard Log (event type ARTEFACT_SUSPECTED → RISK-002).

**Risks arising from the measure (§7.5).** The new hazardous situation is "a real abrupt change is flagged as an artefact". Its effect is bounded: critical values always alarm, and a non-critical alarm is delayed by at most one reading (1 s). This falls inside RISK-009 (smart validation delays a real deterioration), which was re-evaluated with S = 4 and P = 2 unchanged. No new RISK record was needed.

**Effectiveness and residual risk.** RCM-002b only detects **abrupt** in-range artefacts. Gradual artefacts (poor perfusion, a probe slowly slipping) are not detected. With the **default** thresholds, any SpO₂ drop of more than 15 points ends at ≤ 84 %, which is already critical. So the SpO₂ rule mainly adds information to a HIGH alarm, and it changes the counting only when a patient has lowered thresholds (e.g. non-critical < 88 %, critical < 80 %). For these reasons **P of RISK-002 is not lowered**: residual stays 3×2 = 6, ALARP. It will be re-estimated with Hazard Log counts from the simulator artefact scenarios in R3/R4.

Further measures considered and found not practicable:

- a signal-quality index from the device: simulated devices do not provide one, and real devices are out of scope;
- cross-checking HR from ECG against the pulse rate from the oximeter: the data contract has only one HR channel.

**Verification.** `tests/test_alarm_engine.py`, tests tagged `TC-002 / REQ-002`: HR jump flagged and not counted, isolated spike, no reset of a running window, SpO₂ drop vs rise, change equal to the limit, no reference after a gap, configurable limits. `test_artefact_never_masks_a_critical_value` (tagged `TC-015 / REQ-015, REQ-002`) covers decision 1.

**SRS impact (for PLN-01).** REQ-015 counts "consecutive valid readings". A suspected artefact is valid in the REQ-002 sense but is not counted. Proposed sentence for the acceptance criteria of REQ-002/REQ-015: *"A plausible reading whose change from the previous reading exceeds the RCM-002b limits is reported as ARTEFACT_SUSPECTED (LOW) and is not counted in the confirmation window; critical values are never suppressed."*

### 3.2 RCM-005b — escalation of unacknowledged HIGH alarms (RISK-005)

**Proposal evaluated.** A HIGH alarm that is still unacknowledged after **60 s** is re-alerted: the banner and sound are repeated and the alarm is marked "unacknowledged > 60 s". This repeats every 60 s until it is acknowledged, and each re-alert is recorded.

**Decision: accepted, in scope for Sprint 3. Proposed SRS priority: Should.**

The reasons:

- **The ALARP principle applies.** RISK-005 stays at ALARP (3×2 = 6) after RCM-005, and the measure is practicable. In the engine it is a periodic check like `check_data_loss(now)`. In the dashboard it repeats the existing HIGH banner and sound. So it should be implemented.
- **It cannot be done in Sprint 2.** Escalation needs the acknowledgement state of REQ-007 (persisted `Alarm` with `state`, `acknowledged_by` and `acknowledged_at`) and the WebSocket push. Both arrive in Sprint 3. A hook is documented in `backend/app/alarm/engine.py`.
- **Benefit.** It lowers the probability that a HIGH alarm stays unnoticed at the central station. The expected residual is 3×1 = 3 (acceptable), but this is **claimed only after verification** in R3. Until then the register keeps 3×2 = 6.
- **Risks arising from the measure (§7.5).** More audible alarms could increase alarm fatigue, which is part of RISK-005 itself. This is limited by applying escalation only to **HIGH** alarms (MEDIUM and LOW are not escalated in v1), using a 60 s interval, and stopping as soon as the alarm is acknowledged.
- **Alternative rejected.** Escalating to another person (pager, phone, second user) needs a mobile channel, which is out of scope.

Why "Should" and not "Must": without RCM-005b the residual RISK-005 is still ALARP with a documented justification. If R3 runs out of time, the R4 residual risk evaluation must explain why it was not implemented.

**Actions:**

- Project & Standards Lead: add the requirement to the SRS with the next free REQ number (REQ-021 stays reserved), linked to RISK-005.
- Risk Management Lead: implement `check_escalation(now)` in ARC-003, with tests.
- Frontend & Test Lead: implement the repeated banner and sound in ARC-008.

### 3.3 Threshold rationale

The values below are **educational defaults, configurable per patient** (only by a Doctor, REQ-006). They are **not clinical advice**. The numbers are the same as in A6 / SRS / dashboard mock data and were **not changed** in this sprint.

| Vital | Non-critical (MEDIUM after 5 consecutive readings) | Critical (immediate HIGH) |
| --- | --- | --- |
| SpO₂ | < 92 % | < 85 % |
| HR | < 50 or > 120 bpm | < 40 or > 150 bpm |
| Systolic BP | < 90 or > 180 mmHg | none in v1 |
| Diastolic BP | none by default (can be set per patient) | none in v1 |

**Boundary rule.** A value **equal to** a limit is normal. Only strictly `<` or `>` is a violation. One unambiguous rule is used by the SRS, the engine (`Limit.violated_by`), the tests and the dashboard. Readings are integers, so each limit is the last normal value. This avoids off-by-one disagreements between documents and code. The same strict rule is used for the RCM-002b change limits. Boundary tests: `test_non_critical_boundaries` and `test_critical_boundaries` (TC-015).

**Literature check (PLN-03).** The defaults were compared with the Royal College of Physicians' *National Early Warning Score 2* (NEWS2, 2017), which UK wards use to trigger escalation of care.

- **SpO₂ < 92 %** alarms at ≤ 91 %. This is exactly NEWS2 Scale 1's highest-scoring band (≤ 91 % = 3 points).
  - **Critical < 85 %** is severe hypoxaemia, well below that band, so an immediate HIGH alarm without confirmation is justified (RCM-009).
  - Patients with a prescribed target of 88–92 % (hypercapnic respiratory failure; NEWS2 Scale 2, used only on a clinician's decision) would get constant alarms with the defaults. This is the main reason thresholds are **configurable per patient**. The tests use 88 % / 80 % as an example override.
- **HR** non-critical < 50 / > 120 bpm lies in the NEWS2 bands that score 1 (41–50) and 2 (111–130).
  - Critical < 40 / > 150 bpm is beyond the 3-point bands (≤ 40, ≥ 131).
  - The critical high limit (150) is deliberately above 131. NEWS2 is an escalation score, not an immediate alarm, and sinus tachycardia of 121–150 bpm (fever, pain) still gets a MEDIUM alarm after 5 s. An immediate HIGH alarm there would mainly add alarm fatigue (RISK-005).
- **Systolic BP < 90 mmHg** matches NEWS2's 3-point band (≤ 90).
  - **> 180 mmHg** follows the "hypertensive crisis" level (systolic > 180 and/or diastolic > 120 mmHg) of the 2017 ACC/AHA high blood pressure guideline.
- **Known differences (raised for team review, numbers kept).** Because of the strict rule, **HR = 40** is non-critical in MediTrace (NEWS2: 3 points) and **systolic = 90** is normal (NEWS2: 3 points). Both differences are one unit at the edge. HR = 40 still gets a MEDIUM alarm after 5 s. The team agreed numbers are kept, and the team decides at the Sprint 2 review whether to move the limits to 41 / 91.

**Why no critical bypass for blood pressure in v1:**

- Non-invasive cuff BP is measured intermittently and is prone to motion artefacts. A single extreme value should not raise a HIGH alarm.
- Dangerous hypotension usually comes with HR and/or SpO₂ changes, and those do have a critical bypass.
- The bedside monitor keeps its own BP alarms (external control).
- The 1 Hz BP from the simulator is not realistic for cuff measurements (RSK-04).

This is revisited in the R4 residual risk evaluation together with RISK-009.

**References:**

- Royal College of Physicians. *National Early Warning Score (NEWS) 2: Standardising the assessment of acute-illness severity in the NHS.* London: RCP, 2017.
- Whelton P.K. et al. *2017 ACC/AHA/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults.* Hypertension 71(6), e13–e115.
- IEC 60601-1-8 (alarm priorities). Only previews were available (RSK-01).

## 4. Changes to S / P in this sprint

| Risk | Change | Reason |
| --- | --- | --- |
| – | **No S or P value changed in Sprint 2.** | All initial values from Report 1 are kept. |
| RISK-002 | RCM-002b added; residual **not** lowered (3×2) | The measure detects only abrupt artefacts (§3.1). P is to be re-estimated with Hazard Log data in R3/R4. |
| RISK-005 | RCM-005b accepted for R3; residual target 3×1 recorded, current residual still 3×2 | The reduction is claimed only after verification (plan §6). |
| RISK-009 | Re-evaluated because of RCM-002b, S/P unchanged | Worst-case extra delay of one reading for non-critical alarms. Critical values are never suppressed. |
| All | REQ and TC columns extended with the SRS v2 requirements (REQ-018 – REQ-024) that reference these risks | Traceability (plan §6) |

## 5. Open points

1. R3: wire the engine into ingestion (ARC-002) and a 1 Hz `check_data_loss` scheduler. Push alarms over WebSocket (REQ-004).
2. R3: acknowledgement (REQ-007). HIGH alarms latch until acknowledged even if the condition clears. Persisted `Alarm` records with `state`. Then RCM-005b.
3. R3: register a patient at device pairing, so data loss is detected even before the first reading arrives (today only patients that have sent at least one reading are checked).
4. R3: Hazard Log (ARC-004) entries for ARTEFACT_SUSPECTED and DATA_LOSS. First P review with simulator fault-scenario data.
5. Compliance reporter (RCM-010): some tests verify only part of a requirement. Examples: TC-002 is split between the ingestion range check and the engine's RCM-002b, and TC-015 covers the engine but not the dashboard. The report should not show a REQ as fully verified from a partial test alone. To be discussed with the Project & Standards Lead.
6. The engine tracks one alarm episode per vital, not per direction. If a vital moves from the high side straight to the low side (e.g. HR 130 → 45) without a normal reading in between, the HR alarm stays active and is not lost. However, no new event with the new value is raised (unless the new value is critical). For v1 this is accepted: such a jump is first flagged by RCM-002b, and the vital is still shown as alarming. Review in R3, when alarm records carry the latest value.
7. Team decision on the HR 40 / systolic 90 boundary differences from NEWS2 (§3.3).

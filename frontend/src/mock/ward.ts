/**
 * Mock ward for the Sprint 2 dashboard skeleton (ARC-008, PLN-06).
 *
 * SIMULATED DATA ONLY — no real patient data (educational project). Values are chosen with
 * the default thresholds of A6 so that every card status (normal / warning / alarm /
 * data loss) appears at least once. Sprint 3 replaces this module with GET /patients,
 * GET /patients/{id}/readings, GET /alarms and WS /ws/alarms.
 */
import type { Alarm, HazardEvent, Patient, Reading } from '../types'

interface Profile {
  patient: Patient
  base: Pick<Reading, 'hr' | 'sys_bp' | 'dia_bp' | 'spo2'>
  /** Seconds between the newest reading and `now`. */
  age: number
  /** Overrides for the newest readings, oldest first (applied to the tail). */
  tail?: Array<Partial<Pick<Reading, 'hr' | 'sys_bp' | 'dia_bp' | 'spo2' | 'valid'>>>
}

const RECENT = 8 // readings kept per patient for the cards (1 Hz)

const PROFILES: Profile[] = [
  {
    patient: { id: 'P-001', display_name: 'Sim Patient 01', bed: 'Bed 1', device_id: 'DEV-001' },
    base: { hr: 72, sys_bp: 122, dia_bp: 78, spo2: 97 },
    age: 1,
  },
  {
    // warning: HR > 120 for 3 consecutive readings (MEDIUM needs 5, REQ-015)
    patient: { id: 'P-002', display_name: 'Sim Patient 02', bed: 'Bed 2', device_id: 'DEV-002' },
    base: { hr: 112, sys_bp: 131, dia_bp: 84, spo2: 95 },
    age: 1,
    tail: [{ hr: 118 }, { hr: 121 }, { hr: 124 }, { hr: 126 }],
  },
  {
    // alarm: SpO₂ 83 % < 85 % critical → immediate HIGH (critical bypass, RISK-009)
    patient: { id: 'P-003', display_name: 'Sim Patient 03', bed: 'Bed 3', device_id: 'DEV-003' },
    base: { hr: 96, sys_bp: 118, dia_bp: 72, spo2: 94 },
    age: 1,
    tail: [{ spo2: 93 }, { spo2: 90 }, { spo2: 88 }, { spo2: 86 }, { spo2: 83, hr: 104 }],
  },
  {
    // alarm: HR > 120 for 7 consecutive readings → MEDIUM raised at the 5th (RISK-005)
    patient: { id: 'P-004', display_name: 'Sim Patient 04', bed: 'Bed 4', device_id: 'DEV-004' },
    base: { hr: 108, sys_bp: 142, dia_bp: 88, spo2: 96 },
    age: 1,
    tail: [{ hr: 126 }, { hr: 127 }, { hr: 129 }, { hr: 128 }, { hr: 130 }, { hr: 131 }, { hr: 129 }],
  },
  {
    // data loss: newest valid reading 14 s ago → HIGH technical alarm after 10 s (REQ-003)
    patient: { id: 'P-005', display_name: 'Sim Patient 05', bed: 'Bed 5', device_id: 'DEV-005' },
    base: { hr: 81, sys_bp: 127, dia_bp: 80, spo2: 96 },
    age: 14,
  },
  {
    // normal, but a suspected artefact 5 s ago (HR jump > 60 bpm in 1 s, RCM-002b) → LOW
    patient: { id: 'P-006', display_name: 'Sim Patient 06', bed: 'Bed 6', device_id: 'DEV-006' },
    base: { hr: 75, sys_bp: 119, dia_bp: 76, spo2: 98 },
    age: 1,
    tail: [{ hr: 74 }, { hr: 140 }, { hr: 76 }, { hr: 75 }, { hr: 74 }, { hr: 75 }],
  },
  {
    // warning: systolic 88/87 < 90 for 2 readings
    patient: { id: 'P-007', display_name: 'Sim Patient 07', bed: 'Bed 7', device_id: 'DEV-007' },
    base: { hr: 66, sys_bp: 95, dia_bp: 61, spo2: 97 },
    age: 2,
    tail: [{ sys_bp: 92 }, { sys_bp: 88 }, { sys_bp: 87 }],
  },
  {
    // normal, one implausible reading (HR 350 > 300) marked invalid and hazard-logged (REQ-002)
    patient: { id: 'P-008', display_name: 'Sim Patient 08', bed: 'Bed 8', device_id: 'DEV-008' },
    base: { hr: 69, sys_bp: 124, dia_bp: 79, spo2: 99 },
    age: 1,
    tail: [{ hr: 70 }, { hr: 350, valid: false }, { hr: 69 }, { hr: 70 }],
  },
]

export interface MockWard {
  now: Date
  patients: Patient[]
  readings: Record<string, Reading[]>
  alarms: Alarm[]
  hazards: HazardEvent[]
  unpairedDevices: string[]
}

const iso = (now: Date, secondsAgo: number) => new Date(now.getTime() - secondsAgo * 1000).toISOString()

function recentReadings(p: Profile, now: Date): Reading[] {
  const tail = p.tail ?? []
  return Array.from({ length: RECENT }, (_, i) => {
    const secondsAgo = p.age + (RECENT - 1 - i)
    const override = tail[i - (RECENT - tail.length)] ?? {}
    return {
      patient_id: p.patient.id,
      device_id: p.patient.device_id,
      timestamp: iso(now, secondsAgo),
      ...p.base,
      valid: true,
      ...override,
    }
  })
}

/** Build the mock ward relative to `now` (deterministic for a given `now`). */
export function buildMockWard(now: Date = new Date()): MockWard {
  const patients = PROFILES.map((p) => p.patient)
  const readings = Object.fromEntries(PROFILES.map((p) => [p.patient.id, recentReadings(p, now)]))

  const alarms: Alarm[] = [
    { id: 'A-1001', patient_id: 'P-006', kind: 'ARTEFACT_SUSPECTED', priority: 'LOW', vital: 'hr', value: 140, timestamp: iso(now, 5), state: 'ACTIVE', risk_id: 'RISK-002' },
    { id: 'A-1002', patient_id: 'P-004', kind: 'THRESHOLD', priority: 'MEDIUM', vital: 'hr', value: 130, timestamp: iso(now, 3), state: 'ACTIVE', risk_id: 'RISK-005' },
    { id: 'A-1003', patient_id: 'P-003', kind: 'THRESHOLD', priority: 'HIGH', vital: 'spo2', value: 83, timestamp: iso(now, 1), state: 'ACTIVE', risk_id: 'RISK-009' },
    { id: 'A-1004', patient_id: 'P-005', kind: 'DATA_LOSS', priority: 'HIGH', vital: null, value: null, timestamp: iso(now, 4), state: 'ACTIVE', risk_id: 'RISK-001' },
    {
      id: 'A-0997', patient_id: 'P-001', kind: 'THRESHOLD', priority: 'MEDIUM', vital: 'sys_bp', value: 184,
      timestamp: iso(now, 2700), state: 'ACKNOWLEDGED', acknowledged_by: 'dr.demo', acknowledged_at: iso(now, 2610), risk_id: 'RISK-005',
    },
  ]

  const hazards: HazardEvent[] = [
    { id: 'H-0501', timestamp: iso(now, 3), patient_id: 'P-008', device_id: 'DEV-008', event_type: 'IMPLAUSIBLE_VALUE', risk_id: 'RISK-002', detail: 'hr=350 outside 20–300 bpm; reading marked invalid' },
    { id: 'H-0500', timestamp: iso(now, 4), patient_id: 'P-005', device_id: 'DEV-005', event_type: 'DATA_LOSS', risk_id: 'RISK-001', detail: 'no valid reading for 10 s' },
    { id: 'H-0499', timestamp: iso(now, 5), patient_id: 'P-006', device_id: 'DEV-006', event_type: 'ARTEFACT_SUSPECTED', risk_id: 'RISK-002', detail: 'hr 74 → 140 within 1 s (RCM-002b)' },
    { id: 'H-0498', timestamp: iso(now, 620), patient_id: null, device_id: 'DEV-099', event_type: 'UNPAIRED_DEVICE', risk_id: 'RISK-008', detail: 'reading from unpaired device rejected' },
    { id: 'H-0497', timestamp: iso(now, 1800), patient_id: null, device_id: null, event_type: 'AUTH_FAILURE', risk_id: 'RISK-006', detail: '5 failed logins for user "nurse.x"; account locked 15 min' },
  ]

  return { now, patients, readings, alarms, hazards, unpairedDevices: ['DEV-099'] }
}

export function baseProfile(patientId: string): Profile['base'] | undefined {
  return PROFILES.find((p) => p.patient.id === patientId)?.base
}

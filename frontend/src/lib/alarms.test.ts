import { describe, expect, it } from 'vitest'
import type { Alarm } from '../types'
import { acknowledgeAlarm, activeAlarms, hasActiveHigh, sortAlarms } from './alarms'

const at = (s: number) => new Date(Date.UTC(2026, 10, 14, 9, 0, s)).toISOString()

function alarm(id: string, priority: Alarm['priority'], second: number, state: Alarm['state'] = 'ACTIVE'): Alarm {
  return { id, patient_id: 'P-001', kind: 'THRESHOLD', priority, vital: 'hr', value: 130, timestamp: at(second), state, risk_id: 'RISK-005' }
}

describe('alarm ordering (ARC-008)', () => {
  it('TC-005 / REQ-005: alarms are sorted HIGH → MEDIUM → LOW, oldest first within a priority', () => {
    const input = [alarm('a', 'LOW', 1), alarm('b', 'MEDIUM', 2), alarm('c', 'HIGH', 9), alarm('d', 'LOW', 0), alarm('e', 'HIGH', 3), alarm('f', 'MEDIUM', 1)]
    const sorted = sortAlarms(input)
    expect(sorted.map((a) => a.priority)).toEqual(['HIGH', 'HIGH', 'MEDIUM', 'MEDIUM', 'LOW', 'LOW'])
    expect(sorted.map((a) => a.id)).toEqual(['e', 'c', 'f', 'b', 'd', 'a'])
    expect(input.map((a) => a.id)).toEqual(['a', 'b', 'c', 'd', 'e', 'f']) // input not mutated
  })

  it('TC-005 / REQ-005: only ACTIVE HIGH alarms trigger the banner/sound condition', () => {
    expect(hasActiveHigh([alarm('a', 'MEDIUM', 1), alarm('b', 'LOW', 2)])).toBe(false)
    expect(hasActiveHigh([alarm('a', 'HIGH', 1, 'ACKNOWLEDGED')])).toBe(false)
    expect(hasActiveHigh([alarm('a', 'HIGH', 1, 'ACKNOWLEDGED'), alarm('b', 'HIGH', 2)])).toBe(true)
    expect(activeAlarms([alarm('a', 'HIGH', 1, 'ACKNOWLEDGED'), alarm('b', 'LOW', 2)]).map((a) => a.id)).toEqual(['b'])
  })
})

describe('acknowledgement (ARC-008)', () => {
  const now = new Date('2026-11-14T09:31:00.000Z')

  it('TC-007 / REQ-007: acknowledging records the user and the UTC time and leaves the original alarm unchanged', () => {
    const high = alarm('h', 'HIGH', 5)
    const acked = acknowledgeAlarm(high, { username: 'nurse.demo', role: 'Nurse' }, now)
    expect(acked).toMatchObject({ id: 'h', state: 'ACKNOWLEDGED', acknowledged_by: 'nurse.demo', acknowledged_at: '2026-11-14T09:31:00.000Z' })
    expect(high.state).toBe('ACTIVE')
  })

  it('TC-007 / REQ-007: an alarm that is not ACTIVE cannot be acknowledged again', () => {
    const acked = acknowledgeAlarm(alarm('h', 'HIGH', 5), { username: 'dr.demo', role: 'Doctor' }, now)
    expect(() => acknowledgeAlarm(acked, { username: 'nurse.demo', role: 'Nurse' }, now)).toThrow(/only ACTIVE/)
  })

  // Not tagged with a TC: hiding/refusing in the UI is not the REQ-009 verification (that is
  // the backend endpoint × role test TC-009, Sprint 3). Tagging it would let the compliance
  // reporter show REQ-009 as covered too early (RISK-010).
  it('role matrix (A6): Admin and Auditor may not acknowledge', () => {
    expect(() => acknowledgeAlarm(alarm('h', 'HIGH', 5), { username: 'admin.demo', role: 'Admin' }, now)).toThrow(/may not/)
    expect(() => acknowledgeAlarm(alarm('h', 'HIGH', 5), { username: 'auditor.demo', role: 'Auditor' }, now)).toThrow(/may not/)
  })
})

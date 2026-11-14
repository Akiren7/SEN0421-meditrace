/**
 * Card status rules. Not tagged with TC IDs on purpose: REQ-003 / REQ-015 are verified on the
 * Alarm Engine (tests/test_alarm_engine.py, TC-003 / TC-015). These tests only check that
 * the dashboard displays the same rules (A6 thresholds) and that the mock ward is complete.
 */
import { describe, expect, it } from 'vitest'
import { buildMockWard } from '../mock/ward'
import type { Reading } from '../types'
import { formatAge, patientStatus, violationStreak, vitalLevel } from './status'

const NOW = new Date('2026-11-14T09:30:00.000Z')

function readings(values: Array<Partial<Reading>>, ageOfLast = 1): Reading[] {
  return values.map((v, i) => ({
    patient_id: 'P-X',
    device_id: 'DEV-X',
    timestamp: new Date(NOW.getTime() - (ageOfLast + values.length - 1 - i) * 1000).toISOString(),
    hr: 70,
    sys_bp: 120,
    dia_bp: 80,
    spo2: 97,
    valid: true,
    ...v,
  }))
}

describe('vital levels (A6 default thresholds)', () => {
  it('a value equal to a limit is normal; strictly outside is a violation', () => {
    expect(vitalLevel('hr', 120)).toBe('normal')
    expect(vitalLevel('hr', 121)).toBe('non-critical')
    expect(vitalLevel('hr', 150)).toBe('non-critical')
    expect(vitalLevel('hr', 151)).toBe('critical')
    expect(vitalLevel('hr', 50)).toBe('normal')
    expect(vitalLevel('hr', 39)).toBe('critical')
    expect(vitalLevel('spo2', 92)).toBe('normal')
    expect(vitalLevel('spo2', 91)).toBe('non-critical')
    expect(vitalLevel('spo2', 85)).toBe('non-critical')
    expect(vitalLevel('spo2', 84)).toBe('critical')
    expect(vitalLevel('sys_bp', 89)).toBe('non-critical')
    expect(vitalLevel('sys_bp', 40)).toBe('non-critical') // no critical BP limit in v1
    expect(vitalLevel('dia_bp', 30)).toBe('normal') // no default diastolic limits in v1
  })
})

describe('patient card status', () => {
  it('4 violating readings → warning, 5 → alarm (smart validation display)', () => {
    expect(patientStatus(readings([{}, { hr: 125 }, { hr: 125 }, { hr: 125 }, { hr: 125 }]), NOW)).toBe('warning')
    expect(patientStatus(readings([{ hr: 125 }, { hr: 125 }, { hr: 125 }, { hr: 125 }, { hr: 125 }]), NOW)).toBe('alarm')
  })

  it('a critical value is an alarm at once (critical bypass)', () => {
    expect(patientStatus(readings([{}, {}, { spo2: 84 }]), NOW)).toBe('alarm')
  })

  it('invalid readings are ignored: they neither alarm nor break a streak', () => {
    expect(patientStatus(readings([{}, { hr: 350, valid: false }]), NOW)).toBe('normal')
    const r = readings([{ hr: 125 }, { hr: 125 }, { hr: 300, valid: false }, { hr: 125 }, { hr: 125 }, { hr: 125 }])
    expect(violationStreak(r, 'hr')).toBe(5)
  })

  it('data loss at 10 s without a valid reading, not at 9 s', () => {
    expect(patientStatus(readings([{}], 9), NOW)).toBe('normal')
    expect(patientStatus(readings([{}], 10), NOW)).toBe('data_loss')
    expect(patientStatus([], NOW)).toBe('data_loss')
    // An invalid reading does not count as "data received".
    const r = [...readings([{}], 12), ...readings([{ valid: false }], 1)]
    expect(patientStatus(r, NOW)).toBe('data_loss')
  })

  it('the mock ward contains at least one patient in every status', () => {
    const ward = buildMockWard(NOW)
    const statuses = new Set(ward.patients.map((p) => patientStatus(ward.readings[p.id], NOW)))
    expect([...statuses].sort()).toEqual(['alarm', 'data_loss', 'normal', 'warning'])
  })

  it('formats the time since the last reading', () => {
    expect(formatAge(undefined, NOW)).toBe('never')
    expect(formatAge('2026-11-14T09:29:56.000Z', NOW)).toBe('4 s ago')
    expect(formatAge('2026-11-14T09:27:00.000Z', NOW)).toBe('3 min ago')
  })
})

import type { Alarm, AlarmPriority, User } from '../types'
import { VITAL_LABEL, VITAL_UNIT } from './thresholds'

/** IEC 60601-1-8 priority order: HIGH before MEDIUM before LOW. */
export const PRIORITY_RANK: Record<AlarmPriority, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 }

// Implements REQ-005
/**
 * Sort alarms by priority (HIGH → MEDIUM → LOW); within one priority the oldest alarm
 * (waiting longest) comes first. Returns a new array.
 */
export function sortAlarms(alarms: readonly Alarm[]): Alarm[] {
  return [...alarms].sort(
    (a, b) =>
      PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority] ||
      Date.parse(a.timestamp) - Date.parse(b.timestamp) ||
      a.id.localeCompare(b.id),
  )
}

export function activeAlarms(alarms: readonly Alarm[]): Alarm[] {
  return sortAlarms(alarms.filter((a) => a.state === 'ACTIVE'))
}

/** True while at least one HIGH alarm is unacknowledged → red banner + audible alert (REQ-005). */
export function hasActiveHigh(alarms: readonly Alarm[]): boolean {
  return alarms.some((a) => a.state === 'ACTIVE' && a.priority === 'HIGH')
}

// Implements REQ-007
// Controls RISK-005
/**
 * Acknowledge one ACTIVE alarm: the only way an ACTIVE alarm leaves the active list
 * in the dashboard. Records who acknowledged it and when (UTC).
 * Sprint 3: replaced by POST /alarms/{id}/ack (server records user/time + audit entry).
 */
export function acknowledgeAlarm(alarm: Alarm, user: User, now: Date): Alarm {
  if (alarm.state !== 'ACTIVE') {
    throw new Error(`Alarm ${alarm.id} is ${alarm.state}, only ACTIVE alarms can be acknowledged`)
  }
  if (user.role !== 'Doctor' && user.role !== 'Nurse') {
    throw new Error(`Role ${user.role} may not acknowledge alarms`)
  }
  return { ...alarm, state: 'ACKNOWLEDGED', acknowledged_by: user.username, acknowledged_at: now.toISOString() }
}

/** Human-readable alarm text, e.g. "SpO₂ 83 %" or "No valid reading for ≥ 10 s (data loss)". */
export function describeAlarm(alarm: Alarm): string {
  if (alarm.kind === 'DATA_LOSS' || alarm.vital === null) return 'No valid reading for ≥ 10 s (data loss)'
  const reading = `${VITAL_LABEL[alarm.vital]} ${alarm.value} ${VITAL_UNIT[alarm.vital]}`
  return alarm.kind === 'ARTEFACT_SUSPECTED' ? `Suspected artefact: ${reading}` : reading
}

import { VITALS, type PatientStatus, type Reading, type Vital } from '../types'
import {
  CONFIRMATION_READINGS,
  DATA_LOSS_TIMEOUT_MS,
  DEFAULT_THRESHOLDS,
  violates,
  type Thresholds,
} from './thresholds'

export type VitalLevel = 'normal' | 'non-critical' | 'critical'

export function vitalLevel(vital: Vital, value: number, thresholds: Thresholds = DEFAULT_THRESHOLDS): VitalLevel {
  const t = thresholds[vital]
  if (violates(t.critical, value)) return 'critical'
  if (violates(t.nonCritical, value)) return 'non-critical'
  return 'normal'
}

/** Valid readings only (REQ-002: invalid readings are excluded from alarm evaluation), oldest first. */
export function validReadings(readings: readonly Reading[]): Reading[] {
  return readings.filter((r) => r.valid).sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp))
}

/** Number of trailing consecutive valid readings in which `vital` violates a limit. */
export function violationStreak(readings: readonly Reading[], vital: Vital, thresholds: Thresholds = DEFAULT_THRESHOLDS): number {
  const valid = validReadings(readings)
  let streak = 0
  for (let i = valid.length - 1; i >= 0; i--) {
    if (vitalLevel(vital, valid[i][vital], thresholds) === 'normal') break
    streak++
  }
  return streak
}

/**
 * Card status of one patient, using the same rules as the Alarm Engine (ARC-003):
 * - `data_loss`: no valid reading for ≥ 10 s (REQ-003);
 * - `alarm`: latest valid reading is critical (immediate HIGH) or a non-critical violation
 *   persisted for ≥ 5 consecutive valid readings (MEDIUM) (REQ-015);
 * - `warning`: latest valid reading violates a non-critical limit, not yet confirmed;
 * - `normal`: otherwise.
 * Display only — the authoritative alarm decision stays in the backend.
 */
export function patientStatus(
  readings: readonly Reading[],
  now: Date,
  thresholds: Thresholds = DEFAULT_THRESHOLDS,
): PatientStatus {
  const valid = validReadings(readings)
  const last = valid.at(-1)
  if (!last || now.getTime() - Date.parse(last.timestamp) >= DATA_LOSS_TIMEOUT_MS) return 'data_loss'

  let warning = false
  for (const vital of VITALS) {
    const level = vitalLevel(vital, last[vital], thresholds)
    if (level === 'critical') return 'alarm'
    if (level === 'non-critical') {
      if (violationStreak(valid, vital, thresholds) >= CONFIRMATION_READINGS) return 'alarm'
      warning = true
    }
  }
  return warning ? 'warning' : 'normal'
}

export const STATUS_LABEL: Record<PatientStatus, string> = {
  normal: 'Normal',
  warning: 'Warning',
  alarm: 'Alarm',
  data_loss: 'Data loss',
}

/** "4 s ago", "2 min ago", "never". */
export function formatAge(timestamp: string | undefined, now: Date): string {
  if (!timestamp) return 'never'
  const seconds = Math.max(0, Math.floor((now.getTime() - Date.parse(timestamp)) / 1000))
  if (seconds < 60) return `${seconds} s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  return `${Math.floor(minutes / 60)} h ago`
}

/** HH:MM:SS in UTC — the data contract is UTC, the label says so. */
export function formatUtcTime(iso: string): string {
  return `${iso.slice(11, 19)} UTC`
}

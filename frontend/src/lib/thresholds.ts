import type { Vital } from '../types'

/**
 * Default alarm thresholds of A6 — educational defaults, configurable per patient,
 * not clinical advice. Mirrors backend/app/alarm/models.py (ARC-003).
 * A value equal to a limit is normal; a violation is strictly `<` low or `>` high.
 */
export interface Limit {
  low?: number
  high?: number
}

export interface VitalThresholds {
  nonCritical: Limit
  critical: Limit
}

export type Thresholds = Record<Vital, VitalThresholds>

export const DEFAULT_THRESHOLDS: Thresholds = {
  hr: { nonCritical: { low: 50, high: 120 }, critical: { low: 40, high: 150 } },
  // No critical bypass for blood pressure in v1.
  sys_bp: { nonCritical: { low: 90, high: 180 }, critical: {} },
  // No default diastolic limits in v1; a Doctor may set them per patient (Sprint 3).
  dia_bp: { nonCritical: {}, critical: {} },
  spo2: { nonCritical: { low: 92 }, critical: { low: 85 } },
}

/** REQ-015: consecutive valid violating readings before a MEDIUM alarm. */
export const CONFIRMATION_READINGS = 5

/** REQ-003: silence (ms) after which a patient is in "data loss" (`>=`). */
export const DATA_LOSS_TIMEOUT_MS = 10_000

export function violates(limit: Limit, value: number): boolean {
  return (limit.low !== undefined && value < limit.low) || (limit.high !== undefined && value > limit.high)
}

export const VITAL_LABEL: Record<Vital, string> = {
  hr: 'HR',
  sys_bp: 'Systolic BP',
  dia_bp: 'Diastolic BP',
  spo2: 'SpO₂',
}

export const VITAL_UNIT: Record<Vital, string> = {
  hr: 'bpm',
  sys_bp: 'mmHg',
  dia_bp: 'mmHg',
  spo2: '%',
}

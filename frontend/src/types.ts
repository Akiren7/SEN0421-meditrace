/**
 * Shared data contract (Part A6 of the sprint brief, IEEE 1016 Information viewpoint).
 *
 * Field names are identical to the backend (ARC-002 Ingestion, ARC-003 Alarm Engine,
 * ARC-004 Hazard Log) so that the Sprint 3 REST/WebSocket payloads can be used without
 * mapping. All timestamps are ISO 8601 strings in UTC (e.g. "2026-11-14T09:30:00.000Z").
 */

export type Vital = 'hr' | 'sys_bp' | 'dia_bp' | 'spo2'

export const VITALS: readonly Vital[] = ['hr', 'sys_bp', 'dia_bp', 'spo2']

/** Reading (out) — GET /patients/{id}/readings. Invalid readings are kept but never alarm. */
export interface Reading {
  patient_id: string
  device_id: string
  timestamp: string
  hr: number
  sys_bp: number
  dia_bp: number
  spo2: number
  valid: boolean
}

export type AlarmKind = 'THRESHOLD' | 'DATA_LOSS' | 'ARTEFACT_SUSPECTED'
export type AlarmPriority = 'HIGH' | 'MEDIUM' | 'LOW'
export type AlarmState = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED'

export interface Alarm {
  id: string
  patient_id: string
  kind: AlarmKind
  priority: AlarmPriority
  /** null for technical alarms (DATA_LOSS). */
  vital: Vital | null
  value: number | null
  timestamp: string
  state: AlarmState
  acknowledged_by?: string | null
  acknowledged_at?: string | null
  /** RISK-001 data loss · RISK-002 artefact · RISK-005 smart validation · RISK-009 critical bypass */
  risk_id: string
}

export type HazardEventType =
  | 'IMPLAUSIBLE_VALUE'
  | 'UNPAIRED_DEVICE'
  | 'DATA_LOSS'
  | 'ARTEFACT_SUSPECTED'
  | 'AUTH_FAILURE'

export interface HazardEvent {
  id: string
  timestamp: string
  patient_id: string | null
  device_id: string | null
  event_type: HazardEventType
  risk_id: string
  detail: string
}

/** Event type → risk mapping of A6 (used to check mock data and, later, API data). */
export const HAZARD_RISK: Record<HazardEventType, string> = {
  IMPLAUSIBLE_VALUE: 'RISK-002',
  UNPAIRED_DEVICE: 'RISK-008',
  DATA_LOSS: 'RISK-001',
  ARTEFACT_SUSPECTED: 'RISK-002',
  AUTH_FAILURE: 'RISK-006',
}

/** Roles of REQ-009. Real authentication (ARC-005) arrives in Sprint 3. */
export type Role = 'Admin' | 'Doctor' | 'Nurse' | 'Auditor'

export const ROLES: readonly Role[] = ['Doctor', 'Nurse', 'Admin', 'Auditor']

export interface User {
  username: string
  role: Role
}

/** Dashboard-only view model: a bed in the ward with its paired device. */
export interface Patient {
  id: string
  display_name: string
  bed: string
  device_id: string
}

/** Status shown on a patient card (derived in lib/status.ts). */
export type PatientStatus = 'normal' | 'warning' | 'alarm' | 'data_loss'

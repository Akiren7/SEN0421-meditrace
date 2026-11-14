import type { Role } from '../types'

/**
 * Role permission matrix (A6, REQ-009). The dashboard only hides what a role may not do;
 * enforcement is server-side in ARC-005 (Sprint 3), so hiding a button here is NOT a
 * risk control on its own (RISK-004, RISK-006).
 */
export type Action =
  | 'view_patients' // patients, vitals, alarms
  | 'ack_alarm'
  | 'change_thresholds'
  | 'manage_devices_users'
  | 'read_audit_log'
  | 'read_hazard_log'

export const PERMISSIONS: Record<Action, readonly Role[]> = {
  view_patients: ['Doctor', 'Nurse'],
  ack_alarm: ['Doctor', 'Nurse'],
  change_thresholds: ['Doctor'],
  manage_devices_users: ['Admin'],
  read_audit_log: ['Auditor'],
  read_hazard_log: ['Doctor', 'Auditor'],
}

export const ACTION_LABEL: Record<Action, string> = {
  view_patients: 'View patients, vitals, alarms',
  ack_alarm: 'Acknowledge alarm',
  change_thresholds: 'Change thresholds',
  manage_devices_users: 'Pair devices, manage users',
  read_audit_log: 'Read audit log',
  read_hazard_log: 'Read hazard log',
}

export function can(role: Role | undefined, action: Action): boolean {
  return role !== undefined && PERMISSIONS[action].includes(role)
}

/** First screen after login for each role. */
export function homePath(role: Role): string {
  if (can(role, 'view_patients')) return '/patients'
  if (role === 'Admin') return '/admin'
  return '/logs'
}

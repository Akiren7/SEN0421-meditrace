import { createContext, useContext } from 'react'
import type { AlarmSound } from '../lib/beep'
import type { MockWard } from '../mock/ward'
import type { Alarm, User } from '../types'

export interface SessionValue {
  user: User | null
  login(user: User): void
  logout(): void
}

export interface WardValue {
  ward: MockWard
  /** Clock used for "time since last reading" and status (mock snapshot time in Sprint 2). */
  now: Date
  alarms: Alarm[]
  acknowledge(alarmId: string): void
  muted: boolean
  setMuted(muted: boolean): void
  sound: AlarmSound
  healthCheck(): Promise<boolean>
}

export const SessionContext = createContext<SessionValue | null>(null)
export const WardContext = createContext<WardValue | null>(null)

export function useSession(): SessionValue {
  const value = useContext(SessionContext)
  if (!value) throw new Error('useSession must be used inside <DashboardProvider>')
  return value
}

export function useWard(): WardValue {
  const value = useContext(WardContext)
  if (!value) throw new Error('useWard must be used inside <DashboardProvider>')
  return value
}

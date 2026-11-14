import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { acknowledgeAlarm } from '../lib/alarms'
import { createAlarmSound, type AlarmSound } from '../lib/beep'
import { buildMockWard, type MockWard } from '../mock/ward'
import { defaultHealthCheck } from '../lib/health'
import type { User } from '../types'
import { SessionContext, WardContext, type SessionValue, type WardValue } from './contexts'

interface Props {
  children: ReactNode
  /** Injection points for tests; defaults are the real implementations. */
  ward?: MockWard
  initialUser?: User | null
  sound?: AlarmSound
  healthCheck?: () => Promise<boolean>
  /** Clock for acknowledgement times; defaults to the real clock. */
  clock?: () => Date
}

export function DashboardProvider({ children, ward: wardProp, initialUser = null, sound: soundProp, healthCheck = defaultHealthCheck, clock }: Props) {
  const [ward] = useState(() => wardProp ?? buildMockWard())
  const [sound] = useState(() => soundProp ?? createAlarmSound())
  const [user, setUser] = useState<User | null>(initialUser)
  const [alarms, setAlarms] = useState(ward.alarms)
  const [muted, setMuted] = useState(false)

  const logout = useCallback(() => {
    sound.stop()
    setUser(null)
  }, [sound])

  const session = useMemo<SessionValue>(() => ({ user, login: setUser, logout }), [user, logout])

  const acknowledge = useCallback(
    (alarmId: string) => {
      if (!user) return
      const at = clock ? clock() : new Date()
      setAlarms((current) => current.map((a) => (a.id === alarmId ? acknowledgeAlarm(a, user, at) : a)))
    },
    [user, clock],
  )

  const wardValue = useMemo<WardValue>(
    () => ({ ward, now: ward.now, alarms, acknowledge, muted, setMuted, sound, healthCheck }),
    [ward, alarms, acknowledge, muted, sound, healthCheck],
  )

  return (
    <SessionContext.Provider value={session}>
      <WardContext.Provider value={wardValue}>{children}</WardContext.Provider>
    </SessionContext.Provider>
  )
}

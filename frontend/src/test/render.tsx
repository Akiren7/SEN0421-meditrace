import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi, type Mock } from 'vitest'
import { App } from '../App'
import type { AlarmSound } from '../lib/beep'
import { buildMockWard } from '../mock/ward'
import { DashboardProvider } from '../state/DashboardProvider'
import type { User } from '../types'

/** Fixed mock snapshot time so tests are deterministic. */
export const NOW = new Date('2026-11-14T09:30:00.000Z')
/** Fixed time used as "acknowledged_at". */
export const ACK_TIME = new Date('2026-11-14T09:31:00.000Z')

export interface FakeSound extends AlarmSound {
  unlock: Mock<() => void>
  start: Mock<() => void>
  stop: Mock<() => void>
}

export function fakeSound(): FakeSound {
  let playing = false
  return {
    unlock: vi.fn<() => void>(),
    start: vi.fn<() => void>(() => {
      playing = true
    }),
    stop: vi.fn<() => void>(() => {
      playing = false
    }),
    get playing() {
      return playing
    },
  }
}

export const NURSE: User = { username: 'nurse.demo', role: 'Nurse' }
export const DOCTOR: User = { username: 'dr.demo', role: 'Doctor' }
export const ADMIN: User = { username: 'admin.demo', role: 'Admin' }
export const AUDITOR: User = { username: 'auditor.demo', role: 'Auditor' }

export function renderApp({ route = '/', user = null as User | null, sound = fakeSound() } = {}) {
  const ward = buildMockWard(NOW)
  const result = render(
    <MemoryRouter initialEntries={[route]}>
      <DashboardProvider ward={ward} initialUser={user} sound={sound} healthCheck={() => Promise.resolve(false)} clock={() => ACK_TIME}>
        <App />
      </DashboardProvider>
    </MemoryRouter>,
  )
  return { ...result, ward, sound }
}

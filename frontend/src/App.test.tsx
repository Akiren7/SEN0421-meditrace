/**
 * Screen-level tests: login, ward overview, patient detail and the role permission matrix (A6).
 * Role tests are deliberately NOT tagged TC-009 / TC-006: hiding controls in the UI does not
 * verify REQ-009 / REQ-006, which are enforced and tested on the API (ARC-005, Sprint 3).
 */
import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { ADMIN, AUDITOR, DOCTOR, NURSE, renderApp } from './test/render'

describe('login (demo, no real auth)', () => {
  it('signing in with a selected role opens that role’s first screen and unlocks audio', async () => {
    const user = userEvent.setup()
    const { sound } = renderApp({ route: '/login' })
    await user.click(screen.getByRole('radio', { name: 'Doctor' }))
    await user.click(screen.getByRole('button', { name: 'Sign in as Doctor' }))
    expect(screen.getByRole('heading', { name: 'Ward overview' })).toBeInTheDocument()
    expect(screen.getByTestId('user-chip')).toHaveTextContent('dr.demo · Doctor')
    expect(sound.unlock).toHaveBeenCalled()
  })

  it('protected screens redirect to the login page when nobody is signed in', () => {
    renderApp({ route: '/alarms' })
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })
})

describe('ward overview', () => {
  it('shows one card per patient with HR, BP, SpO₂, status and time since last reading, most urgent first', () => {
    const { ward } = renderApp({ route: '/patients', user: NURSE })
    const cards = screen.getAllByTestId('patient-card')
    expect(cards).toHaveLength(ward.patients.length)
    expect(cards.map((c) => c.dataset.status)).toEqual(['alarm', 'alarm', 'data_loss', 'warning', 'warning', 'normal', 'normal', 'normal'])

    const bed5 = cards.find((c) => c.textContent?.includes('Bed 5'))!
    expect(bed5).toHaveTextContent('Data loss')
    expect(bed5).toHaveTextContent('Last reading: 14 s ago')
    const bed3 = cards.find((c) => c.textContent?.includes('Bed 3'))!
    expect(within(bed3).getByText('83')).toHaveClass('v--critical')
    expect(bed3).toHaveTextContent('1 active alarm')
  })
})

describe('patient detail', () => {
  it('shows latest values and the downsampled 24-h chart for HR and SpO₂', () => {
    renderApp({ route: '/patients/P-003', user: NURSE })
    expect(screen.getByRole('heading', { name: /Bed 3/ })).toBeInTheDocument()
    expect(screen.getByLabelText('Heart rate last 24 hours')).toBeInTheDocument()
    expect(screen.getByLabelText('Blood pressure last 24 hours')).toBeInTheDocument()
    expect(screen.getByLabelText('SpO₂ last 24 hours')).toBeInTheDocument()
    expect(screen.getByTestId('chart-stats')).toHaveTextContent(/valid readings in the last 24 h → 1000 plotted points per vital/)
  })
})

describe('role permission matrix (A6) in the UI', () => {
  it('Doctor sees "Edit thresholds", Nurse does not; both can acknowledge', () => {
    const doctor = renderApp({ route: '/patients/P-003', user: DOCTOR })
    expect(screen.getByRole('button', { name: /Edit thresholds/ })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Acknowledge' }).length).toBeGreaterThan(0)
    doctor.unmount()

    renderApp({ route: '/patients/P-003', user: NURSE })
    expect(screen.queryByRole('button', { name: /Edit thresholds/ })).toBeNull()
    expect(screen.getAllByRole('button', { name: 'Acknowledge' }).length).toBeGreaterThan(0)
  })

  it.each([ADMIN, AUDITOR])('$role sees no patient vitals, no alarms and no Acknowledge button', (who) => {
    const { sound } = renderApp({ route: '/patients', user: who })
    expect(screen.getByRole('heading', { name: '403 — Not permitted' })).toBeInTheDocument()
    expect(screen.queryAllByTestId('patient-card')).toHaveLength(0)
    expect(screen.queryByRole('link', { name: 'Patients' })).toBeNull()
    expect(screen.queryByRole('link', { name: /^Alarms/ })).toBeNull()
    expect(screen.queryByTestId('high-alarm-banner')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Acknowledge' })).toBeNull()
    expect(sound.start).not.toHaveBeenCalled()
  })

  it('Admin gets the device pairing screen; Auditor gets the hazard and audit log; Nurse may not open the logs', () => {
    const admin = renderApp({ route: '/', user: ADMIN })
    expect(screen.getByRole('heading', { name: 'Devices & users' })).toBeInTheDocument()
    admin.unmount()

    const auditor = renderApp({ route: '/', user: AUDITOR })
    expect(screen.getByTestId('hazard-log')).toHaveTextContent('UNPAIRED_DEVICE')
    expect(screen.getByRole('heading', { name: /Audit log/ })).toBeInTheDocument()
    auditor.unmount()

    renderApp({ route: '/logs', user: NURSE })
    expect(screen.getByRole('heading', { name: '403 — Not permitted' })).toBeInTheDocument()
  })
})

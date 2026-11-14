import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { DOCTOR, NURSE, renderApp } from '../test/render'

const activeRows = () => within(screen.getByTestId('active-alarms')).getAllByTestId('alarm-row')
const row = (id: string) => document.querySelector<HTMLElement>(`[data-alarm-id="${id}"]`)!

describe('alarm screen', () => {
  it('TC-005 / REQ-005: active alarms are listed HIGH → MEDIUM → LOW and a HIGH alarm shows the red banner and plays the sound', () => {
    const { sound } = renderApp({ route: '/alarms', user: NURSE })

    const priorities = activeRows().map((r) => within(r).getByText(/^(HIGH|MEDIUM|LOW)$/).textContent)
    expect(priorities).toEqual(['HIGH', 'HIGH', 'MEDIUM', 'LOW'])

    const banner = screen.getByTestId('high-alarm-banner')
    expect(banner).toHaveAttribute('role', 'alert')
    expect(banner).toHaveTextContent('2 HIGH alarms active')
    expect(sound.start).toHaveBeenCalled()
  })

  it('TC-005 / REQ-005: muting (demo toggle) stops the sound but keeps the visual banner', async () => {
    const user = userEvent.setup()
    const { sound } = renderApp({ route: '/alarms', user: NURSE })
    expect(sound.playing).toBe(true)
    await user.click(screen.getByRole('button', { name: /mute for demo/i }))
    expect(sound.playing).toBe(false)
    expect(screen.getByTestId('high-alarm-banner')).toBeInTheDocument()
  })

  it('TC-007 / REQ-007: a HIGH alarm stays active until acknowledged; acknowledging records user and time', async () => {
    const user = userEvent.setup()
    renderApp({ route: '/alarms', user: NURSE })
    const high = row('A-1003') // Bed 3, SpO₂ 83 (critical)

    // No other way to dismiss: the only control is "Acknowledge".
    expect(within(high).getAllByRole('button').map((b) => b.textContent)).toEqual(['Acknowledge'])
    expect(within(high).queryByRole('button', { name: /dismiss|close|clear|resolve/i })).toBeNull()

    // Opening and cancelling the confirmation keeps the alarm active.
    await user.click(within(high).getByRole('button', { name: 'Acknowledge' }))
    await user.click(within(high).getByRole('button', { name: 'Cancel' }))
    expect(activeRows().map((r) => r.dataset.alarmId)).toContain('A-1003')

    // Navigating away and back does not clear it either; the banner is shown on other screens.
    await user.click(screen.getByRole('link', { name: 'Patients' }))
    expect(screen.getByTestId('high-alarm-banner')).toHaveTextContent('Bed 3')
    await user.click(screen.getByRole('link', { name: /^Alarms/ }))
    expect(activeRows().map((r) => r.dataset.alarmId)).toContain('A-1003')

    // Acknowledge → confirm.
    await user.click(within(row('A-1003')).getByRole('button', { name: 'Acknowledge' }))
    expect(within(row('A-1003')).getByText('Acknowledge as Nurse?')).toBeInTheDocument()
    await user.click(within(row('A-1003')).getByRole('button', { name: 'Confirm' }))

    expect(activeRows().map((r) => r.dataset.alarmId)).not.toContain('A-1003')
    const acked = within(screen.getByTestId('acknowledged-alarms'))
      .getAllByTestId('alarm-row')
      .find((r) => r.dataset.alarmId === 'A-1003')!
    expect(within(acked).getByTestId('ack-info')).toHaveTextContent('Acknowledged by nurse.demo at 09:31:00 UTC')
  })

  it('TC-022 / REQ-022: starting from the patient list, a HIGH alarm is acknowledged with at most 2 clicks', async () => {
    const user = userEvent.setup()
    renderApp({ route: '/patients', user: NURSE })
    let clicks = 0
    const click = async (el: HTMLElement) => {
      clicks++
      await user.click(el)
    }
    const inBanner = () => document.querySelector<HTMLElement>('[data-banner-alarm-id="A-1003"]')!

    expect(screen.getByRole('heading', { name: 'Ward overview' })).toBeInTheDocument()
    await click(within(inBanner()).getByRole('button', { name: 'Acknowledge' }))
    expect(within(inBanner()).getByText('Acknowledge as Nurse?')).toBeInTheDocument()
    await click(within(inBanner()).getByRole('button', { name: 'Confirm' }))

    expect(clicks).toBeLessThanOrEqual(2)
    expect(document.querySelector('[data-banner-alarm-id="A-1003"]')).toBeNull()
    await user.click(screen.getByRole('link', { name: /^Alarms/ }))
    expect(row('A-1003')).toHaveTextContent('Acknowledged by nurse.demo at 09:31:00 UTC')
  })

  it('TC-022 / REQ-022: on the alarm screen any active alarm is acknowledged with 2 clicks', async () => {
    const user = userEvent.setup()
    renderApp({ route: '/alarms', user: DOCTOR })
    await user.click(within(row('A-1002')).getByRole('button', { name: 'Acknowledge' }))
    await user.click(within(row('A-1002')).getByRole('button', { name: 'Confirm' }))
    expect(activeRows().map((r) => r.dataset.alarmId)).not.toContain('A-1002')
    expect(row('A-1002')).toHaveTextContent('Acknowledged by dr.demo')
  })

  it('TC-007 / REQ-007: the banner and the sound stop only after every HIGH alarm is acknowledged', async () => {
    const user = userEvent.setup()
    const { sound } = renderApp({ route: '/alarms', user: NURSE })
    for (const id of ['A-1003', 'A-1004']) {
      expect(screen.getByTestId('high-alarm-banner')).toBeInTheDocument()
      await user.click(within(row(id)).getByRole('button', { name: 'Acknowledge' }))
      await user.click(within(row(id)).getByRole('button', { name: 'Confirm' }))
    }
    expect(screen.queryByTestId('high-alarm-banner')).toBeNull()
    expect(sound.playing).toBe(false)
    // MEDIUM and LOW alarms are still active.
    expect(activeRows().map((r) => r.dataset.alarmId)).toEqual(['A-1002', 'A-1001'])
  })
})

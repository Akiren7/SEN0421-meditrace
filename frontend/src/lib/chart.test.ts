import { describe, expect, it } from 'vitest'
import { DAY_SECONDS, generateReadings } from '../mock/history'
import { buildMockWard } from '../mock/ward'
import type { Reading } from '../types'
import { last24h, prepareChartData, WINDOW_MS } from './chart'

const NOW = new Date('2026-11-14T09:30:00.000Z')

/** One reading every 2 min over the last 30 h (901 readings, < 1 000 in the window); every 7th is invalid. */
function seed30h(): Reading[] {
  const out: Reading[] = []
  for (let m = 30 * 60; m >= 0; m -= 2) {
    out.push({
      patient_id: 'P-X',
      device_id: 'DEV-X',
      timestamp: new Date(NOW.getTime() - m * 60_000).toISOString(),
      hr: 60 + (m % 20),
      sys_bp: 110 + (m % 30),
      dia_bp: 70 + (m % 10),
      spo2: 94 + (m % 5),
      valid: (m / 2) % 7 !== 3,
    })
  }
  return out.reverse() // newest first: the window function must sort
}

describe('24-h trend chart data', () => {
  it('TC-014 / REQ-014: with 30 h of readings, exactly the valid readings in [now − 24 h, now] are charted, in time order', () => {
    const readings = seed30h()
    const window = last24h(readings, NOW)
    const expected = readings.filter((r) => r.valid && Date.parse(r.timestamp) >= NOW.getTime() - WINDOW_MS && Date.parse(r.timestamp) <= NOW.getTime())

    expect(window).toHaveLength(expected.length)
    expect(new Set(window)).toEqual(new Set(expected))
    expect(window.every((r) => r.valid)).toBe(true)
    expect(window.every((r, i) => i === 0 || Date.parse(r.timestamp) > Date.parse(window[i - 1].timestamp))).toBe(true)
    expect(Date.parse(window[0].timestamp)).toBeGreaterThanOrEqual(NOW.getTime() - WINDOW_MS)
    expect(window.at(-1)!.timestamp).toBe(NOW.toISOString())
    // Boundary: the reading exactly 24 h old is inside the window; the one 24 h + 2 min old is not.
    expect(window.some((r) => r.timestamp === new Date(NOW.getTime() - WINDOW_MS).toISOString())).toBe(true)
    expect(window.some((r) => r.timestamp === new Date(NOW.getTime() - WINDOW_MS - 120_000).toISOString())).toBe(false)
  })

  it('TC-014 / REQ-014: HR, systolic BP, diastolic BP and SpO₂ series are produced and no invalid value is plotted', () => {
    const readings = seed30h()
    const chart = prepareChartData(readings, NOW)
    const valid = last24h(readings, NOW)
    expect(Object.keys(chart.series).sort()).toEqual(['dia_bp', 'hr', 'spo2', 'sys_bp'])
    expect(chart.inWindow).toBe(valid.length)
    expect(valid.length).toBeLessThan(1000)
    expect(readings.some((r) => !r.valid)).toBe(true)
    // Under 1 000 points nothing is downsampled: series equal the window values exactly.
    expect(chart.series.hr.map((p) => p.v)).toEqual(valid.map((r) => r.hr))
    expect(chart.series.dia_bp.map((p) => p.v)).toEqual(valid.map((r) => r.dia_bp))
  })

  it('TC-014 / REQ-014: the mock history covers 24 h at 1 Hz and ends with the newest card reading', () => {
    const ward = buildMockWard(NOW)
    const recent = ward.readings['P-003']
    const last = recent.filter((r) => r.valid).at(-1)!
    const history = generateReadings('P-003', 'DEV-003', { hr: 96, sys_bp: 118, dia_bp: 72, spo2: 94 }, new Date(last.timestamp), recent)
    expect(history).toHaveLength(DAY_SECONDS)
    expect(history.at(-1)).toEqual(last)
    expect(history.some((r) => !r.valid)).toBe(true) // exclusion rule is exercised
    const chart = prepareChartData(history, NOW)
    expect(chart.series.spo2.at(-1)!.v).toBe(83)
    expect(Math.min(...chart.series.hr.map((p) => p.v))).toBeGreaterThan(0) // invalid HR 0 never plotted
  })
})

import { describe, expect, it } from 'vitest'
import { DAY_SECONDS, generateReadings } from '../mock/history'
import { buildMockWard } from '../mock/ward'
import { prepareChartData } from './chart'
import { bucketRanges, downsampleMinMax, MAX_CHART_POINTS, type Point } from './downsample'

const END = new Date('2026-11-14T09:30:00.000Z')

function series(n: number, f: (i: number) => number): Point[] {
  return Array.from({ length: n }, (_, i) => ({ t: i * 1000, v: f(i) }))
}

describe('24-h chart downsampling', () => {
  it('TC-023 / REQ-023: 86 400 points are reduced to ≤ 1 000 points that keep the min and max of every bucket', () => {
    // Noisy signal with a single 3-second spike and a single 2-second dip.
    const points = series(DAY_SECONDS, (i) => 70 + ((i * 7919) % 13) - 6 + (i >= 40_000 && i < 40_003 ? 90 : 0) - (i >= 70_000 && i < 70_002 ? 40 : 0))
    const out = downsampleMinMax(points)

    expect(out.length).toBeLessThanOrEqual(MAX_CHART_POINTS)
    expect(out.length).toBeGreaterThan(MAX_CHART_POINTS / 2)

    for (const [start, end] of bucketRanges(points.length)) {
      const bucket = points.slice(start, end).map((p) => p.v)
      const kept = out.filter((p) => p.t >= points[start].t && p.t < (points[end]?.t ?? Infinity)).map((p) => p.v)
      expect(kept).toContain(Math.min(...bucket))
      expect(kept).toContain(Math.max(...bucket))
    }
    // Short extremes survive downsampling (they would be averaged away otherwise).
    expect(Math.max(...out.map((p) => p.v))).toBe(Math.max(...points.map((p) => p.v)))
    expect(Math.min(...out.map((p) => p.v))).toBe(Math.min(...points.map((p) => p.v)))
    // Output stays in time order.
    expect(out.every((p, i) => i === 0 || p.t > out[i - 1].t)).toBe(true)
  })

  it('TC-023 / REQ-023: preparing one patient’s 24-h chart data (86 400 readings, 4 vitals) takes well under 2 s', () => {
    const ward = buildMockWard(END)
    const started = performance.now()
    const history = generateReadings('P-003', 'DEV-003', { hr: 96, sys_bp: 118, dia_bp: 72, spo2: 94 }, END, ward.readings['P-003'])
    const chart = prepareChartData(history, END)
    const elapsed = performance.now() - started
    expect(history).toHaveLength(DAY_SECONDS)
    for (const points of Object.values(chart.series)) expect(points.length).toBeLessThanOrEqual(MAX_CHART_POINTS)
    // Data preparation only; the browser timing "open screen → rendered chart ≤ 2 s on a
    // standard laptop, 5 runs" is the TC-023 system measurement in Sprint 4 (test plan §5).
    expect(elapsed).toBeLessThan(1000)
  })

  it('downsampling leaves short series unchanged and rejects maxPoints < 2', () => {
    const short = series(10, (i) => i)
    expect(downsampleMinMax(short)).toEqual(short)
    expect(downsampleMinMax(short)).not.toBe(short)
    expect(() => downsampleMinMax(short, 1)).toThrow(RangeError)
  })
})

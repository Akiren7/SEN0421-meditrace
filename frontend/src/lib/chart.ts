import { VITALS, type Reading, type Vital } from '../types'
import { downsampleMinMax, MAX_CHART_POINTS, type Point } from './downsample'

export const WINDOW_MS = 24 * 60 * 60 * 1000

interface Timed {
  reading: Reading
  t: number
}

/** Valid readings in [now − 24 h, now] with their parsed time, oldest first (each timestamp parsed once). */
function window24h(readings: readonly Reading[], now: Date): Timed[] {
  const to = now.getTime()
  const from = to - WINDOW_MS
  const out: Timed[] = []
  let sorted = true
  for (const reading of readings) {
    if (!reading.valid) continue
    const t = Date.parse(reading.timestamp)
    if (t < from || t > to) continue
    if (out.length > 0 && t < out[out.length - 1].t) sorted = false
    out.push({ reading, t })
  }
  if (!sorted) out.sort((a, b) => a.t - b.t)
  return out
}

// Implements REQ-014
/**
 * Readings for the 24-h chart: only `valid` readings with timestamp in [now − 24 h, now],
 * in time order (SRS REQ-014 acceptance criteria). Invalid readings are never plotted.
 */
export function last24h(readings: readonly Reading[], now: Date): Reading[] {
  return window24h(readings, now).map((x) => x.reading)
}

export interface ChartData {
  series: Record<Vital, Point[]>
  /** Valid readings in the window, before downsampling. */
  inWindow: number
  /** Points plotted per vital after downsampling (≤ 1 000). */
  plotted: number
}

// Implements REQ-014, REQ-023
/** Window → one series per vital → min/max downsampling to ≤ 1 000 points per vital. */
export function prepareChartData(readings: readonly Reading[], now: Date, maxPoints: number = MAX_CHART_POINTS): ChartData {
  const window = window24h(readings, now)
  const out = {} as Record<Vital, Point[]>
  for (const vital of VITALS) {
    out[vital] = downsampleMinMax(
      window.map(({ reading, t }) => ({ t, v: reading[vital] })),
      maxPoints,
    )
  }
  return { series: out, inWindow: window.length, plotted: out.hr.length }
}

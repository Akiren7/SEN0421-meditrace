/**
 * Mock reading history for the patient-detail chart (REQ-014, REQ-023).
 * One reading per second → 86 400 readings for a full day, as GET /patients/{id}/readings
 * would return at 1 Hz. About 0.05 % of readings are implausible and marked `valid = false`
 * (as ARC-002 would do) so the chart's exclusion rule is exercised. SIMULATED DATA ONLY.
 */
import type { Reading } from '../types'

export const DAY_SECONDS = 86_400

/** Small deterministic PRNG (mulberry32) so charts and tests are reproducible. */
function prng(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function seedOf(text: string): number {
  let h = 2166136261
  for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619)
  return h >>> 0
}

type Base = Pick<Reading, 'hr' | 'sys_bp' | 'dia_bp' | 'spo2'>

/**
 * `seconds` readings at 1 Hz ending at `end`: circadian sine + slow random walk + noise + a
 * few short excursions. `recent` (the newest readings shown on the card) replace the tail so
 * the chart ends at the card values.
 */
export function generateReadings(
  patientId: string,
  deviceId: string,
  base: Base,
  end: Date,
  recent: readonly Reading[] = [],
  seconds: number = DAY_SECONDS,
): Reading[] {
  const rand = prng(seedOf(patientId))
  const endMs = end.getTime()
  const out: Reading[] = new Array(seconds)
  let walk = 0
  let walkSpo2 = 0
  let excursion = 0
  for (let i = 0; i < seconds; i++) {
    const phase = (2 * Math.PI * i) / DAY_SECONDS
    walk = Math.max(-8, Math.min(8, walk + (rand() - 0.5) * 0.3))
    walkSpo2 = Math.max(-1.5, Math.min(1.5, walkSpo2 + (rand() - 0.5) * 0.05))
    if (excursion === 0 && rand() < 0.00004) excursion = 120 + Math.floor(rand() * 240)
    const exc = excursion > 0 ? 1 : 0
    if (excursion > 0) excursion--
    const implausible = rand() < 0.0005
    out[i] = {
      patient_id: patientId,
      device_id: deviceId,
      timestamp: new Date(endMs - (seconds - 1 - i) * 1000).toISOString(),
      hr: implausible ? 0 : Math.round(base.hr + 6 * Math.sin(phase) + walk + (rand() - 0.5) * 3 + exc * 18),
      sys_bp: Math.round(base.sys_bp + 8 * Math.sin(phase) + walk * 0.8 + (rand() - 0.5) * 4),
      dia_bp: Math.round(base.dia_bp + 5 * Math.sin(phase) + walk * 0.5 + (rand() - 0.5) * 3),
      spo2: Math.min(100, Math.round(base.spo2 + 0.8 * Math.sin(phase) + walkSpo2 + (rand() - 0.5) - exc * 4)),
      valid: !implausible,
    }
  }
  for (const r of recent) {
    const idx = seconds - 1 - Math.round((endMs - Date.parse(r.timestamp)) / 1000)
    if (idx >= 0 && idx < seconds) out[idx] = r
  }
  return out
}

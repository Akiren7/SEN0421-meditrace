/** One chart point: time in ms since epoch (UTC) and a value. */
export interface Point {
  t: number
  v: number
}

export const MAX_CHART_POINTS = 1000

// Implements REQ-023
/**
 * Min/max bucket downsampling for the 24-h chart (REQ-014, REQ-023).
 *
 * The series (sorted by time) is split into `floor(maxPoints / 2)` buckets of equal size;
 * each bucket contributes its minimum and its maximum point, in time order. Unlike
 * averaging, this keeps short extreme values (e.g. a brief desaturation) visible, which
 * matters for a clinical trend view. 86 400 points (24 h × 1 Hz) → 1 000 points.
 *
 * Returns the input unchanged (copied) when it already has ≤ `maxPoints` points.
 */
export function downsampleMinMax(points: readonly Point[], maxPoints: number = MAX_CHART_POINTS): Point[] {
  if (maxPoints < 2) throw new RangeError('maxPoints must be at least 2')
  if (points.length <= maxPoints) return points.slice()

  const buckets = Math.floor(maxPoints / 2)
  const size = points.length / buckets
  const out: Point[] = []
  for (let b = 0; b < buckets; b++) {
    const start = Math.floor(b * size)
    const end = Math.min(points.length, Math.floor((b + 1) * size))
    let min = start
    let max = start
    for (let i = start + 1; i < end; i++) {
      if (points[i].v < points[min].v) min = i
      if (points[i].v > points[max].v) max = i
    }
    if (min === max) {
      out.push(points[min])
    } else {
      out.push(points[Math.min(min, max)], points[Math.max(min, max)])
    }
  }
  return out
}

/** Bucket boundaries used by downsampleMinMax (exported for tests). */
export function bucketRanges(length: number, maxPoints: number = MAX_CHART_POINTS): Array<[number, number]> {
  const buckets = Math.floor(maxPoints / 2)
  const size = length / buckets
  return Array.from({ length: buckets }, (_, b) => [Math.floor(b * size), Math.min(length, Math.floor((b + 1) * size))])
}

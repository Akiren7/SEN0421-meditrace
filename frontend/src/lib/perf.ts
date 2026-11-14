/**
 * Browser performance timing for REQ-023 ("time from opening the patient detail screen to the
 * fully rendered chart"). The mark is set in the click handler that opens the screen; the
 * measure is taken one animation frame after the charts are committed. Without a mark (page
 * opened by URL) the time since navigation start is used.
 */
export const OPEN_MARK = 'meditrace:open-patient-detail'
const MEASURE = 'meditrace:patient-detail-rendered'

export function markDetailOpen(): void {
  try {
    performance.clearMarks(OPEN_MARK)
    performance.mark(OPEN_MARK)
  } catch {
    // Performance API unavailable: the on-screen timing is simply not shown.
  }
}

export function measureSinceDetailOpen(): number | undefined {
  try {
    const hasMark = performance.getEntriesByName(OPEN_MARK, 'mark').length > 0
    const measure = hasMark ? performance.measure(MEASURE, OPEN_MARK) : performance.measure(MEASURE)
    performance.clearMarks(OPEN_MARK)
    return measure.duration
  } catch {
    return undefined
  }
}

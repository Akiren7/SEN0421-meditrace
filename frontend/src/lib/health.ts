/** GET /health through the Vite dev proxy (/api → http://localhost:8000). Optional badge only. */
export async function defaultHealthCheck(): Promise<boolean> {
  try {
    const response = await fetch('/api/health', { signal: AbortSignal.timeout(2000) })
    if (!response.ok) return false
    const body: unknown = await response.json()
    return typeof body === 'object' && body !== null && (body as { status?: unknown }).status === 'ok'
  } catch {
    return false
  }
}

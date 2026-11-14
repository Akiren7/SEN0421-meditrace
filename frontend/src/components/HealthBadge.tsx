import { useEffect, useState } from 'react'
import { useWard } from '../state/contexts'

type HealthState = 'checking' | 'online' | 'offline'

/** Optional backend status from GET /health. The dashboard itself runs on mock data. */
export function HealthBadge() {
  const { healthCheck } = useWard()
  const [state, setState] = useState<HealthState>('checking')

  useEffect(() => {
    let cancelled = false
    healthCheck().then((ok) => {
      if (!cancelled) setState(ok ? 'online' : 'offline')
    })
    return () => {
      cancelled = true
    }
  }, [healthCheck])

  const label = { checking: 'checking…', online: 'online', offline: 'offline (mock data)' }[state]
  return (
    <span className={`health health--${state}`} title="GET /health via /api proxy">
      <span className="health__dot" aria-hidden="true" /> Backend: {label}
    </span>
  )
}

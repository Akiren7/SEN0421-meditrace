import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { ACTION_LABEL, can, type Action } from '../lib/permissions'
import { useSession } from '../state/contexts'

/**
 * Route guard mirroring the HTTP 403 of ARC-005 (Sprint 3). UI convenience only:
 * the server remains responsible for enforcing REQ-006 / REQ-009.
 */
export function RequirePermission({ action, children }: { action: Action; children: ReactNode }) {
  const { user } = useSession()
  if (!user) return <Navigate to="/login" replace />
  if (!can(user.role, action)) {
    return (
      <section className="panel forbidden" role="alert">
        <h2>403 — Not permitted</h2>
        <p>
          Role <strong>{user.role}</strong> may not: {ACTION_LABEL[action].toLowerCase()} (role permission matrix, REQ-009).
        </p>
      </section>
    )
  }
  return <>{children}</>
}

import { can, ACTION_LABEL, PERMISSIONS, type Action } from '../lib/permissions'
import { formatUtcTime } from '../lib/status'
import { useSession, useWard } from '../state/contexts'
import { ROLES } from '../types'

function PermissionMatrix() {
  return (
    <table className="table" aria-label="Role permission matrix">
      <thead>
        <tr>
          <th>Action</th>
          {ROLES.map((r) => (
            <th key={r}>{r}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {(Object.keys(PERMISSIONS) as Action[]).map((action) => (
          <tr key={action}>
            <td>{ACTION_LABEL[action]}</td>
            {ROLES.map((r) => (
              <td key={r} className="center">
                {can(r, action) ? '✓' : '–'}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Admin landing page (placeholder): device pairing and users arrive with ARC-005 in Sprint 3. */
export function AdminPage() {
  const { ward } = useWard()
  return (
    <section>
      <div className="page-head">
        <h1>Devices &amp; users</h1>
        <span className="muted">Admin · no access to patient vitals (REQ-009)</span>
      </div>
      <div className="panel">
        <h2>Device pairing (REQ-013) — read-only mock</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Device</th>
              <th>Paired with</th>
            </tr>
          </thead>
          <tbody>
            {ward.patients.map((p) => (
              <tr key={p.device_id}>
                <td>{p.device_id}</td>
                <td>
                  {p.id} ({p.bed})
                </td>
              </tr>
            ))}
            {ward.unpairedDevices.map((d) => (
              <tr key={d}>
                <td>{d}</td>
                <td className="warn">unpaired — readings rejected and hazard-logged</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small">POST /devices/pair and user management screens: Sprint 3.</p>
      </div>
      <div className="panel">
        <h2>Role permission matrix</h2>
        <PermissionMatrix />
      </div>
    </section>
  )
}

/** Hazard log (Doctor, Auditor) and audit log (Auditor) — mock / placeholder. */
export function LogsPage() {
  const { user } = useSession()
  const { ward } = useWard()
  if (!can(user?.role, 'read_hazard_log') && !can(user?.role, 'read_audit_log')) {
    return (
      <section className="panel forbidden" role="alert">
        <h2>403 — Not permitted</h2>
        <p>
          Role <strong>{user?.role}</strong> may not read the hazard or audit log (role permission matrix, REQ-009).
        </p>
      </section>
    )
  }
  return (
    <section>
      <div className="page-head">
        <h1>Logs</h1>
        <span className="muted">{user?.role} · read-only</span>
      </div>
      {can(user?.role, 'read_hazard_log') && (
        <div className="panel">
          <h2>Hazard log (ARC-004, REQ-012) — mock</h2>
          <table className="table" data-testid="hazard-log">
            <thead>
              <tr>
                <th>Time</th>
                <th>Event</th>
                <th>Patient</th>
                <th>Device</th>
                <th>Risk</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {ward.hazards.map((h) => (
                <tr key={h.id}>
                  <td>{formatUtcTime(h.timestamp)}</td>
                  <td>{h.event_type}</td>
                  <td>{h.patient_id ?? '—'}</td>
                  <td>{h.device_id ?? '—'}</td>
                  <td>{h.risk_id}</td>
                  <td>{h.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {can(user?.role, 'read_audit_log') && (
        <div className="panel">
          <h2>Audit log (ARC-006, REQ-011)</h2>
          <p className="muted">Append-only audit log via GET /audit — Sprint 3.</p>
        </div>
      )}
    </section>
  )
}

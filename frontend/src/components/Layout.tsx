import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { activeAlarms } from '../lib/alarms'
import { can } from '../lib/permissions'
import { formatUtcTime } from '../lib/status'
import { useSession, useWard } from '../state/contexts'
import { HealthBadge } from './HealthBadge'
import { HighAlarmBanner } from './HighAlarmBanner'

export function Layout() {
  const { user, logout } = useSession()
  const { alarms, now } = useWard()
  const navigate = useNavigate()
  const role = user?.role
  const clinical = can(role, 'view_patients')
  const activeCount = activeAlarms(alarms).length

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            ♥
          </span>
          MediTrace <span className="brand__sub">Ward 3B · central monitor</span>
        </div>
        <nav className="nav" aria-label="Main">
          {clinical && <NavLink to="/patients">Patients</NavLink>}
          {clinical && (
            <NavLink to="/alarms">
              Alarms {activeCount > 0 && <span className="count">{activeCount}</span>}
            </NavLink>
          )}
          {can(role, 'manage_devices_users') && <NavLink to="/admin">Devices &amp; users</NavLink>}
          {(can(role, 'read_hazard_log') || can(role, 'read_audit_log')) && <NavLink to="/logs">Logs</NavLink>}
        </nav>
        <div className="topbar__right">
          <HealthBadge />
          {user && (
            <span className="user-chip" data-testid="user-chip">
              {user.username} · <strong>{user.role}</strong>
            </span>
          )}
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="mockbar">
        SIMULATED DATA — mock snapshot at {formatUtcTime(now.toISOString())}. Live data via WebSocket in Sprint 3. Not for clinical use.
      </div>
      {clinical && <HighAlarmBanner />}
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}

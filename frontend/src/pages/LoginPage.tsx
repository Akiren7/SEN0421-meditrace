import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { homePath } from '../lib/permissions'
import { useSession, useWard } from '../state/contexts'
import { ROLES, type Role } from '../types'

const DEMO_USER: Record<Role, string> = {
  Doctor: 'dr.demo',
  Nurse: 'nurse.demo',
  Admin: 'admin.demo',
  Auditor: 'auditor.demo',
}

/**
 * Static demo login. NO real authentication: the password is not checked or sent anywhere.
 * Username/password + Argon2 + lockout (REQ-008) and JWT/RBAC (REQ-009) come with ARC-005
 * in Sprint 3; until then the role is chosen here to demonstrate the permission matrix.
 */
export function LoginPage() {
  const { login } = useSession()
  const { sound } = useWard()
  const navigate = useNavigate()
  const [role, setRole] = useState<Role>('Nurse')
  const [username, setUsername] = useState(DEMO_USER.Nurse)
  const [password, setPassword] = useState('')

  const chooseRole = (next: Role) => {
    if (username === DEMO_USER[role]) setUsername(DEMO_USER[next])
    setRole(next)
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    sound.unlock() // user gesture: browsers allow audio from now on (REQ-005 audible alert)
    login({ username: username.trim() || DEMO_USER[role], role })
    navigate(homePath(role))
  }

  return (
    <div className="login">
      <form className="login__card" onSubmit={submit} aria-labelledby="login-title">
        <div className="brand brand--dark">
          <span className="brand__mark" aria-hidden="true">
            ♥
          </span>
          MediTrace
        </div>
        <h1 id="login-title">Sign in</h1>
        <p className="muted">Central vital-sign monitor · Ward 3B</p>

        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" placeholder="not checked in demo" />
        </label>

        <fieldset className="roles">
          <legend>Role (demo switch)</legend>
          {ROLES.map((r) => (
            <label key={r} className={`role ${r === role ? 'role--on' : ''}`}>
              <input type="radio" name="role" value={r} checked={r === role} onChange={() => chooseRole(r)} />
              {r}
            </label>
          ))}
        </fieldset>

        <button type="submit" className="btn btn--primary btn--block">
          Sign in as {role}
        </button>
        <p className="login__note">
          Demo only — no real authentication yet (ARC-005, Sprint 3). Simulated data, not for clinical use.
        </p>
      </form>
    </div>
  )
}

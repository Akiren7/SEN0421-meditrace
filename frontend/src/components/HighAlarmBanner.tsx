import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { activeAlarms, describeAlarm } from '../lib/alarms'
import { useWard } from '../state/contexts'
import { AckControl } from './AckControl'

// Implements REQ-005, REQ-022
// Controls RISK-003, RISK-005
/**
 * Red banner + audible alert while at least one HIGH alarm is ACTIVE. Shown on every clinical
 * screen so a HIGH alarm cannot be missed by navigating away, and each HIGH alarm can be
 * acknowledged from here in 2 clicks (REQ-022: starting from the patient list). Disappears
 * only when every HIGH alarm is acknowledged (REQ-007).
 */
export function HighAlarmBanner() {
  const { alarms, ward, muted, setMuted, sound } = useWard()
  const high = activeAlarms(alarms).filter((a) => a.priority === 'HIGH')
  const active = high.length > 0

  useEffect(() => {
    if (active && !muted) sound.start()
    else sound.stop()
    return () => sound.stop()
  }, [active, muted, sound])

  if (!active) return null
  const bed = (patientId: string) => ward.patients.find((p) => p.id === patientId)?.bed ?? patientId

  return (
    <div className="high-banner" role="alert" aria-live="assertive" data-testid="high-alarm-banner">
      <div className="high-banner__head">
        <span className="high-banner__icon" aria-hidden="true">
          ▲
        </span>
        <strong>
          {high.length} HIGH alarm{high.length > 1 ? 's' : ''} active
        </strong>
        <span className="high-banner__spacer" />
        <Link className="btn btn--ghost-light" to="/alarms">
          All alarms
        </Link>
        <button type="button" className="btn btn--ghost-light" aria-pressed={muted} onClick={() => setMuted(!muted)}>
          {muted ? '🔇 Sound muted (demo)' : '🔊 Mute for demo'}
        </button>
      </div>
      <ul className="high-banner__list">
        {high.map((a) => (
          <li key={a.id} data-banner-alarm-id={a.id}>
            <span>
              <strong>{bed(a.patient_id)}</strong> · {describeAlarm(a)}
            </span>
            <AckControl alarm={a} light />
          </li>
        ))}
      </ul>
    </div>
  )
}

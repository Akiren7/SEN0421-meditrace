import { AlarmRow } from '../components/AlarmRow'
import { sortAlarms } from '../lib/alarms'
import { useWard } from '../state/contexts'

/** Alarm screen: ACTIVE alarms sorted HIGH → MEDIUM → LOW (REQ-005), acknowledged below (REQ-007). */
export function AlarmsPage() {
  const { alarms } = useWard()
  const active = sortAlarms(alarms.filter((a) => a.state === 'ACTIVE'))
  const acknowledged = alarms
    .filter((a) => a.state === 'ACKNOWLEDGED')
    .sort((a, b) => Date.parse(b.acknowledged_at ?? b.timestamp) - Date.parse(a.acknowledged_at ?? a.timestamp))

  return (
    <section>
      <div className="page-head">
        <h1>Alarms</h1>
        <span className="muted">
          {active.length} active · sorted by priority, then oldest first
        </span>
      </div>
      <div className="panel">
        <h2>Active</h2>
        {active.length === 0 ? (
          <p className="muted">No active alarms.</p>
        ) : (
          <ul className="alarms" aria-label="Active alarms" data-testid="active-alarms">
            {active.map((a) => (
              <AlarmRow key={a.id} alarm={a} />
            ))}
          </ul>
        )}
      </div>
      <div className="panel">
        <h2>Acknowledged</h2>
        {acknowledged.length === 0 ? (
          <p className="muted">None yet.</p>
        ) : (
          <ul className="alarms" aria-label="Acknowledged alarms" data-testid="acknowledged-alarms">
            {acknowledged.map((a) => (
              <AlarmRow key={a.id} alarm={a} />
            ))}
          </ul>
        )}
      </div>
      <p className="muted small">
        An ACTIVE alarm can only leave this list by acknowledgement (REQ-007). RESOLVED (value back to normal after acknowledgement) is set by the
        Alarm Engine in Sprint 3.
      </p>
    </section>
  )
}

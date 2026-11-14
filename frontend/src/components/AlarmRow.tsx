import { describeAlarm } from '../lib/alarms'
import { formatUtcTime } from '../lib/status'
import { useWard } from '../state/contexts'
import type { Alarm } from '../types'
import { AckControl } from './AckControl'

/**
 * One alarm in a list. ACTIVE alarms offer only "Acknowledge" — there is no close/dismiss
 * control (REQ-007). Acknowledged alarms show who acknowledged them and when.
 */
export function AlarmRow({ alarm, showPatient = true }: { alarm: Alarm; showPatient?: boolean }) {
  const { ward } = useWard()
  const patient = ward.patients.find((p) => p.id === alarm.patient_id)

  return (
    <li className={`alarm alarm--${alarm.priority.toLowerCase()} alarm--${alarm.state.toLowerCase()}`} data-testid="alarm-row" data-alarm-id={alarm.id}>
      <span className={`prio prio--${alarm.priority.toLowerCase()}`}>{alarm.priority}</span>
      <div className="alarm__body">
        <div className="alarm__title">
          {showPatient && patient && (
            <span className="alarm__bed">
              {patient.bed} · {patient.display_name}
            </span>
          )}
          <span className="alarm__desc">{describeAlarm(alarm)}</span>
        </div>
        <div className="alarm__meta">
          {alarm.kind} · raised {formatUtcTime(alarm.timestamp)} · {alarm.risk_id} · {alarm.id}
        </div>
        {alarm.state === 'ACKNOWLEDGED' && (
          <div className="alarm__ack" data-testid="ack-info">
            Acknowledged by <strong>{alarm.acknowledged_by}</strong> at {alarm.acknowledged_at && formatUtcTime(alarm.acknowledged_at)}
          </div>
        )}
      </div>
      <div className="alarm__actions">
        <AckControl alarm={alarm} />
      </div>
    </li>
  )
}

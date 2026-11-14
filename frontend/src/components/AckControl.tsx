import { useState } from 'react'
import { can } from '../lib/permissions'
import { useSession, useWard } from '../state/contexts'
import type { Alarm } from '../types'

// Implements REQ-007, REQ-022
// Controls RISK-005
/**
 * The only way to take an ACTIVE alarm out of the active list: Acknowledge → "Acknowledge as
 * <role>?" → Confirm. Two clicks (REQ-022), wherever the alarm is shown (HIGH banner on every
 * screen, alarm screen, patient detail). Rendered only for roles allowed to acknowledge.
 */
export function AckControl({ alarm, light = false }: { alarm: Alarm; light?: boolean }) {
  const { user } = useSession()
  const { acknowledge } = useWard()
  const [confirming, setConfirming] = useState(false)
  if (alarm.state !== 'ACTIVE' || !user || !can(user.role, 'ack_alarm')) return null

  if (!confirming) {
    return (
      <button type="button" className={`btn ${light ? 'btn--light' : 'btn--primary'}`} onClick={() => setConfirming(true)}>
        Acknowledge
      </button>
    )
  }
  return (
    <div className="confirm" role="group" aria-label="Confirm acknowledgement">
      <span>Acknowledge as {user.role}?</span>
      <button type="button" className={`btn ${light ? 'btn--light' : 'btn--primary'}`} onClick={() => acknowledge(alarm.id)}>
        Confirm
      </button>
      <button type="button" className={`btn ${light ? 'btn--ghost-light' : 'btn--ghost'}`} onClick={() => setConfirming(false)}>
        Cancel
      </button>
    </div>
  )
}

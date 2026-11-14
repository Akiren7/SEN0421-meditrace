import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { markDetailOpen } from '../lib/perf'
import { formatAge, patientStatus, STATUS_LABEL, validReadings, vitalLevel } from '../lib/status'
import { useWard } from '../state/contexts'
import type { Patient, PatientStatus, Reading, Vital } from '../types'

const ORDER: PatientStatus[] = ['alarm', 'data_loss', 'warning', 'normal']

function Value({ vital, reading, children }: { vital: Vital; reading: Reading; children: ReactNode }) {
  const level = vitalLevel(vital, reading[vital])
  return <span className={`v v--${level}`}>{children}</span>
}

function PatientCard({ patient, readings, now, alarmCount }: { patient: Patient; readings: Reading[]; now: Date; alarmCount: number }) {
  const status = patientStatus(readings, now)
  const last = validReadings(readings).at(-1)
  const invalid = readings.filter((r) => !r.valid).length

  return (
    <Link to={`/patients/${patient.id}`} onClick={markDetailOpen} className={`card card--${status}`} data-testid="patient-card" data-status={status}>
      <div className="card__head">
        <span className="card__bed">{patient.bed}</span>
        <span className={`status status--${status}`}>{STATUS_LABEL[status]}</span>
      </div>
      <div className="card__name">
        {patient.display_name} <span className="muted">· {patient.id}</span>
      </div>
      {last ? (
        <dl className={`card__vitals ${status === 'data_loss' ? 'card__vitals--stale' : ''}`}>
          <div>
            <dt>HR</dt>
            <dd>
              <Value vital="hr" reading={last}>
                {last.hr}
              </Value>
              <small>bpm</small>
            </dd>
          </div>
          <div>
            <dt>BP</dt>
            <dd>
              <Value vital="sys_bp" reading={last}>
                {last.sys_bp}
              </Value>
              /{last.dia_bp}
              <small>mmHg</small>
            </dd>
          </div>
          <div>
            <dt>SpO₂</dt>
            <dd>
              <Value vital="spo2" reading={last}>
                {last.spo2}
              </Value>
              <small>%</small>
            </dd>
          </div>
        </dl>
      ) : (
        <p className="muted">No valid reading</p>
      )}
      <div className="card__foot">
        <span title={last?.timestamp}>Last reading: {formatAge(last?.timestamp, now)}</span>
        {alarmCount > 0 && <span className="pill pill--alarm">{alarmCount} active alarm{alarmCount > 1 ? 's' : ''}</span>}
        {invalid > 0 && <span className="pill">{invalid} invalid excluded</span>}
      </div>
    </Link>
  )
}

/** Ward overview (ARC-008): one card per patient, most urgent first. */
export function PatientListPage() {
  const { ward, now, alarms } = useWard()
  const rows = ward.patients.map((p) => ({ patient: p, readings: ward.readings[p.id] ?? [], status: patientStatus(ward.readings[p.id] ?? [], now) }))
  rows.sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status) || a.patient.bed.localeCompare(b.patient.bed, undefined, { numeric: true }))
  const count = (s: PatientStatus) => rows.filter((r) => r.status === s).length

  return (
    <section>
      <div className="page-head">
        <h1>Ward overview</h1>
        <ul className="legend" aria-label="Status counts">
          {ORDER.map((s) => (
            <li key={s}>
              <span className={`status status--${s}`}>{STATUS_LABEL[s]}</span> {count(s)}
            </li>
          ))}
        </ul>
      </div>
      <div className="grid">
        {rows.map(({ patient, readings }) => (
          <PatientCard
            key={patient.id}
            patient={patient}
            readings={readings}
            now={now}
            alarmCount={alarms.filter((a) => a.patient_id === patient.id && a.state === 'ACTIVE').length}
          />
        ))}
      </div>
      <p className="muted small">
        Status rules (A6 defaults): <b>Alarm</b> = critical value or non-critical violation for ≥ 5 consecutive readings (REQ-015) ·{' '}
        <b>Warning</b> = non-critical violation not yet confirmed · <b>Data loss</b> = no valid reading for ≥ 10 s (REQ-003). Invalid readings are
        excluded (REQ-002).
      </p>
    </section>
  )
}

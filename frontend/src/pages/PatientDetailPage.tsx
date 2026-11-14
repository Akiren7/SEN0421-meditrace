import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlarmRow } from '../components/AlarmRow'
import { VitalChart } from '../components/VitalChart'
import { sortAlarms } from '../lib/alarms'
import { prepareChartData } from '../lib/chart'
import { can } from '../lib/permissions'
import { measureSinceDetailOpen } from '../lib/perf'
import { formatAge, formatUtcTime, patientStatus, STATUS_LABEL, validReadings, vitalLevel } from '../lib/status'
import { DEFAULT_THRESHOLDS, VITAL_LABEL, VITAL_UNIT } from '../lib/thresholds'
import { generateReadings } from '../mock/history'
import { baseProfile } from '../mock/ward'
import { useSession, useWard } from '../state/contexts'
import { VITALS } from '../types'

/**
 * 24-h chart data (REQ-014): mock history of 86 400 readings ending at the newest valid
 * reading, windowed to [now − 24 h, now] and downsampled to ≤ 1 000 points per vital
 * (REQ-023). Sprint 3: generateReadings is replaced by GET /patients/{id}/readings.
 */
function useChartData(patientId: string) {
  const { ward, now } = useWard()
  return useMemo(() => {
    const base = baseProfile(patientId)
    const patient = ward.patients.find((p) => p.id === patientId)
    const recent = ward.readings[patientId] ?? []
    const last = validReadings(recent).at(-1)
    if (!base || !patient || !last) return undefined
    const history = generateReadings(patientId, patient.device_id, base, new Date(last.timestamp), recent)
    return prepareChartData(history, now)
  }, [patientId, ward, now])
}

export function PatientDetailPage() {
  const { patientId = '' } = useParams()
  const { user } = useSession()
  const { ward, now, alarms } = useWard()
  const patient = ward.patients.find((p) => p.id === patientId)
  const readings = ward.readings[patientId] ?? []
  const last = validReadings(readings).at(-1)
  const chart = useChartData(patientId)
  const [renderMs, setRenderMs] = useState<number>()

  useEffect(() => {
    // One frame after the charts are committed: browser timing for REQ-023.
    const frame = requestAnimationFrame(() => setRenderMs(measureSinceDetailOpen()))
    return () => cancelAnimationFrame(frame)
  }, [patientId])

  if (!patient) {
    return (
      <section className="panel">
        <h1>Unknown patient {patientId}</h1>
        <Link to="/patients">Back to ward overview</Link>
      </section>
    )
  }

  const status = patientStatus(readings, now)
  const patientAlarms = sortAlarms(alarms.filter((a) => a.patient_id === patient.id && a.state !== 'RESOLVED'))
  const t = DEFAULT_THRESHOLDS

  return (
    <section>
      <Link to="/patients" className="back">
        ← Ward overview
      </Link>
      <div className="page-head">
        <h1>
          {patient.bed} · {patient.display_name} <span className="muted">({patient.id}, {patient.device_id})</span>
        </h1>
        <span className={`status status--${status} status--lg`}>{STATUS_LABEL[status]}</span>
      </div>

      <div className="tiles">
        {VITALS.map((vital) => (
          <div key={vital} className={`tile tile--${last ? vitalLevel(vital, last[vital]) : 'normal'}`}>
            <div className="tile__label">{VITAL_LABEL[vital]}</div>
            <div className="tile__value">
              {last ? last[vital] : '—'} <small>{VITAL_UNIT[vital]}</small>
            </div>
          </div>
        ))}
        <div className="tile tile--info">
          <div className="tile__label">Last valid reading</div>
          <div className="tile__value tile__value--sm">{formatAge(last?.timestamp, now)}</div>
          <div className="muted small">{last && formatUtcTime(last.timestamp)}</div>
        </div>
      </div>

      <div className="detail-actions">
        {can(user?.role, 'change_thresholds') && (
          <button type="button" className="btn" disabled title="PUT /patients/{id}/thresholds — Sprint 3 (REQ-006)">
            Edit thresholds (Doctor, Sprint 3)
          </button>
        )}
        <span className="muted small">
          Thresholds: HR {t.hr.nonCritical.low}–{t.hr.nonCritical.high} (critical &lt;{t.hr.critical.low} / &gt;{t.hr.critical.high}) · SpO₂ ≥{' '}
          {t.spo2.nonCritical.low} (critical &lt;{t.spo2.critical.low}) · Systolic {t.sys_bp.nonCritical.low}–{t.sys_bp.nonCritical.high}
        </span>
      </div>

      {patientAlarms.length > 0 && (
        <div className="panel">
          <h2>Alarms for this patient</h2>
          <ul className="alarms">
            {patientAlarms.map((a) => (
              <AlarmRow key={a.id} alarm={a} showPatient={false} />
            ))}
          </ul>
        </div>
      )}

      <div className="panel">
        <h2>Last 24 hours</h2>
        {chart ? (
          <>
            <VitalChart
              title="Heart rate"
              unit="bpm"
              domain={[30, 170]}
              series={[{ name: 'HR', color: '#1565c0', points: chart.series.hr }]}
              limits={[
                { value: t.hr.nonCritical.high!, label: '120' },
                { value: t.hr.nonCritical.low!, label: '50' },
                { value: t.hr.critical.high!, label: '150 critical', critical: true },
              ]}
            />
            <VitalChart
              title="Blood pressure"
              unit="mmHg"
              domain={[40, 200]}
              series={[
                { name: 'Systolic', color: '#6a1b9a', points: chart.series.sys_bp },
                { name: 'Diastolic', color: '#ab47bc', points: chart.series.dia_bp },
              ]}
              limits={[
                { value: t.sys_bp.nonCritical.high!, label: 'sys 180' },
                { value: t.sys_bp.nonCritical.low!, label: 'sys 90' },
              ]}
            />
            <VitalChart
              title="SpO₂"
              unit="%"
              domain={[80, 100]}
              series={[{ name: 'SpO₂', color: '#00897b', points: chart.series.spo2 }]}
              limits={[
                { value: t.spo2.nonCritical.low!, label: '92' },
                { value: t.spo2.critical.low!, label: '85 critical', critical: true },
              ]}
            />
            <p className="muted small" data-testid="chart-stats">
              {chart.inWindow.toLocaleString('en')} valid readings in the last 24 h → {chart.plotted} plotted points per vital (min/max
              downsampling, invalid readings excluded)
              {renderMs !== undefined && (
                <>
                  {' '}
                  · screen rendered {Math.round(renderMs)} ms after opening (REQ-023 target ≤ 2 000 ms)
                </>
              )}
            </p>
          </>
        ) : (
          <p className="muted">No data.</p>
        )}
      </div>
    </section>
  )
}

import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Point } from '../lib/downsample'

interface Series {
  name: string
  color: string
  points: Point[]
}

interface Props {
  title: string
  unit: string
  series: Series[]
  domain: [number, number]
  /** Threshold lines (non-critical and critical limits). */
  limits?: Array<{ value: number; label: string; critical?: boolean }>
}

const hhmm = (t: number) => new Date(t).toISOString().slice(11, 16)

// Implements REQ-014
/** 24-h time-series chart of one or two vitals (points already downsampled, REQ-023). */
export function VitalChart({ title, unit, series, domain, limits = [] }: Props) {
  return (
    <figure className="chart" aria-label={`${title} last 24 hours`}>
      <figcaption>
        {title} <span className="muted">({unit}, last 24 h, UTC)</span>
      </figcaption>
      <div className="chart__plot">
        <ResponsiveContainer width="100%" height={200} initialDimension={{ width: 800, height: 200 }}>
          <LineChart margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="#e6e9ef" vertical={false} />
            <XAxis dataKey="t" type="number" domain={['dataMin', 'dataMax']} scale="time" tickFormatter={hhmm} minTickGap={40} fontSize={12} allowDuplicatedCategory={false} />
            <YAxis domain={domain} width={40} fontSize={12} allowDataOverflow />
            <Tooltip labelFormatter={(t) => `${new Date(Number(t)).toISOString().slice(11, 19)} UTC`} formatter={(v, name) => [`${v} ${unit}`, name]} />
            {series.length > 1 && <Legend verticalAlign="top" height={24} iconType="plainline" />}
            {limits.map((l) => (
              <ReferenceLine
                key={`${l.label}-${l.value}`}
                y={l.value}
                stroke={l.critical ? '#c62828' : '#ef8f00'}
                strokeDasharray="4 4"
                label={{ value: l.label, position: 'insideTopRight', fontSize: 11, fill: l.critical ? '#c62828' : '#a35f00' }}
              />
            ))}
            {series.map((s) => (
              <Line key={s.name} data={s.points} name={s.name} type="linear" dataKey="v" stroke={s.color} dot={false} strokeWidth={1.5} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

import { useEffect, useRef, useState } from 'react'
import { go, OPEN, potholes, STATUS, type Report, type Stats, type Status } from '../api'
import { Card, Deadline, Icon, Severity, StatusBadge, type IconName } from '../ui'

// Validated with the dataviz palette checker (light + dark, CVD-safe).
const REPORTED = '#2F6DB5'
const FIXED = '#1A9E8F'

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [w, setW] = useState(600)
  useEffect(() => {
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width))
    if (ref.current) ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w] as const
}

/** Weekly reported vs repaired, one shared y-axis, crosshair tooltip on hover. */
function Trend({ weekly }: { weekly: Stats['weekly'] }) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  const H = 230, L = 34, R = 64, T = 12, B = 26
  const max = Math.max(4, ...weekly.flatMap((w) => [w.reported, w.fixed]))
  const step = Math.ceil(max / 4)
  const top = step * 4
  const x = (i: number) => L + (i * (width - L - R)) / (weekly.length - 1)
  const y = (v: number) => T + (1 - v / top) * (H - T - B)
  const line = (k: 'reported' | 'fixed') => weekly.map((w, i) => `${i ? 'L' : 'M'}${x(i)},${y(w[k])}`).join('')
  const label = (iso: string) => new Date(iso).toLocaleDateString('fr-TN', { day: 'numeric', month: 'short' })
  const last = weekly.length - 1

  return (
    <div ref={ref} className="chart" onMouseLeave={() => setHover(null)}>
      <svg width={width} height={H} role="img" aria-label="Signalements et réparations par semaine">
        {[0, 1, 2, 3, 4].map((k) => (
          <g key={k}>
            <line x1={L} x2={width - R} y1={y(k * step)} y2={y(k * step)} className="grid" />
            <text x={L - 8} y={y(k * step) + 4} textAnchor="end" className="axis">{k * step}</text>
          </g>
        ))}
        {weekly.map((w, i) => (i % 2 === last % 2 ? (
          <text key={w.week} x={x(i)} y={H - 6} textAnchor="middle" className="axis">{label(w.week)}</text>
        ) : null))}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} className="crosshair" />}
        <path d={line('reported')} stroke={REPORTED} className="series" />
        <path d={line('fixed')} stroke={FIXED} className="series" />
        {/* Direct labels at the line ends (plus the legend above). */}
        <text x={x(last) + 8} y={y(weekly[last].reported) + 4} className="end-label">Signalés</text>
        <text x={x(last) + 8} y={y(weekly[last].fixed) + (weekly[last].fixed === weekly[last].reported ? 18 : 4)} className="end-label">Réparés</text>
        {hover != null && (['reported', 'fixed'] as const).map((k) => (
          <circle key={k} cx={x(hover)} cy={y(weekly[hover][k])} r={5} fill={k === 'reported' ? REPORTED : FIXED} className="dot" />
        ))}
        {weekly.map((w, i) => (
          <rect key={w.week} x={x(i) - (width - L - R) / last / 2} y={T} width={(width - L - R) / last} height={H - T - B}
            fill="transparent" onMouseEnter={() => setHover(i)} />
        ))}
      </svg>
      {hover != null && (
        <div className="tooltip" style={{ left: Math.min(x(hover) + 12, width - 170), top: 8 }}>
          <b>Semaine du {label(weekly[hover].week)}</b>
          <span><i style={{ background: REPORTED }} />Signalés <b>{weekly[hover].reported}</b></span>
          <span><i style={{ background: FIXED }} />Réparés <b>{weekly[hover].fixed}</b></span>
        </div>
      )}
    </div>
  )
}

function Kpi({ icon, label, value, hint, tone }: { icon: IconName; label: string; value: string | number; hint: string; tone?: string }) {
  return (
    <div className={`kpi ${tone ?? ''}`}>
      <span className="kpi-icon"><Icon name={icon} /></span>
      <div>
        <div className="kpi-label">{label}</div>
        <div className="kpi-value">{value}</div>
        <div className="kpi-hint">{hint}</div>
      </div>
    </div>
  )
}

export default function Overview({ reports, stats }: { reports: Report[] | null; stats: Stats | null }) {
  if (!reports || !stats) return <div className="loading">Chargement…</div>
  const queue = potholes(reports).filter((r) => OPEN.includes(r.status)).sort((a, b) => b.priority - a.priority).slice(0, 8)
  const total = stats.potholes_total || 1
  const zoneMax = Math.max(1, ...stats.top_zones.map(([, n]) => n))
  const thisWeek = stats.weekly.at(-1)!

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Vue d'ensemble</h1>
          <p className="muted">
            {stats.potholes_total} nids-de-poule suivis · {stats.reports_total} signalements citoyens · mis à jour en continu
          </p>
        </div>
        <a className="btn primary" href="#/assistant"><Icon name="spark" size={15} /> Demander à Sabeel Assist</a>
      </header>

      <div className="kpis">
        <Kpi icon="layers" label="Ouverts" value={stats.open} hint={`${thisWeek.reported} nouveaux cette semaine`} />
        <Kpi icon="alert" label="Urgents" value={stats.urgent_open} hint="sévérité 4 ou 5" tone="critical" />
        <Kpi icon="clock" label="En retard" value={stats.overdue} hint="échéance dépassée" tone="serious" />
        <Kpi icon="check" label="Réparés" value={stats.fixed} hint={`${thisWeek.fixed} cette semaine`} tone="good" />
        <Kpi icon="wrench" label="Délai médian" value={stats.median_repair_days != null ? `${stats.median_repair_days} j` : '—'} hint="du signalement à la réparation" />
      </div>

      <div className="grid-2-1">
        <Card title="Signalements et réparations par semaine" action={
          <span className="legend"><i style={{ background: REPORTED }} />Signalés<i style={{ background: FIXED }} />Réparés</span>
        }>
          <Trend weekly={stats.weekly} />
        </Card>
        <Card title="Par statut">
          <ul className="bars">
            {(Object.keys(STATUS) as Status[]).map((s) => {
              const n = stats.by_status[s] ?? 0
              return (
                <li key={s}>
                  <StatusBadge status={s} />
                  <span className="bar"><span className={`fill tone-${STATUS[s].tone}`} style={{ width: `${(n / total) * 100}%` }} /></span>
                  <b>{n}</b>
                </li>
              )
            })}
          </ul>
          <div className="split">
            {Object.entries(stats.by_office).map(([office, n]) => (
              <div key={office}>
                <span className="muted small">{office === 'Municipality' ? 'Municipalité' : office}</span>
                <b>{n}</b>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid-2-1">
        <Card title="File prioritaire" action={<a className="link" href="#/reports">Tout voir →</a>}>
          <table className="table">
            <thead>
              <tr><th>Réf.</th><th>Adresse</th><th>Sévérité</th><th>Statut</th><th>Citoyens</th><th>Échéance</th></tr>
            </thead>
            <tbody>
              {queue.map((r) => (
                <tr key={r.report_id} onClick={() => go('map', r.report_id)} className="clickable">
                  <td className="mono">{r.ref}</td>
                  <td className="ellipsis">{r.address ?? '—'}</td>
                  <td><Severity score={r.score} /></td>
                  <td><StatusBadge status={r.status} /></td>
                  <td>{r.cluster_size}</td>
                  <td><Deadline r={r} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Quartiers les plus touchés">
          <ul className="bars zones">
            {stats.top_zones.map(([zone, n]) => (
              <li key={zone}>
                <span className="ellipsis">{zone}</span>
                <span className="bar"><span className="fill" style={{ width: `${(n / zoneMax) * 100}%` }} /></span>
                <b>{n}</b>
              </li>
            ))}
          </ul>
          <p className="muted small note">Nids-de-poule ouverts par quartier.</p>
        </Card>
      </div>
    </div>
  )
}

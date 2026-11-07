import { api, go, type Office, type Summary, usePoll } from '../api'
import { Bars, Legend, LineChart, SERIES, weekLabel } from '../components/charts'
import { STATUS } from '../i18n'
import { Card, Deadline, Icon, Kpi, Loading, Priority, Severity, StatusBadge } from '../ui'

const LINES = [
  { key: 'reported', label: 'Signalés', color: SERIES.reported },
  { key: 'confirmed', label: 'Confirmés', color: SERIES.confirmed },
  { key: 'fixed', label: 'Réparés', color: SERIES.fixed },
]

export default function Overview({ office, summary, version }: { office: Office; summary: Summary | null; version: number }) {
  const trend = usePoll(() => api.trend(12), 60000, [version])
  const queue = usePoll(() => api.queue({ status: 'open', limit: 8 }), 30000, [version])
  const weather = usePoll(api.weather, 0)
  const hot = usePoll(api.hotspots, 60000, [version])
  if (!summary) return <Loading />
  const s = summary
  const ttf = s.time_to_fix_days.median

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Vue d'ensemble</h1>
          <p className="muted">{office.name} · {s.potholes_total} nids-de-poule suivis · {s.reports_total} signalements citoyens</p>
        </div>
        <a className="btn primary" href="#/assistant"><Icon name="spark" size={15} /> Demander à Sabeel Assist</a>
      </header>

      {weather.data?.alert && (
        <div className="banner rain" role="status">
          <Icon name="cloud" size={20} />
          <div>
            <b>Pluie prévue : {weather.data.rain_mm_48h} mm dans les 48 h.</b>{' '}
            {weather.data.at_risk} nid(s)-de-poule de sévérité ≥ 3 deviennent prioritaires (eau dans le trou, fondation fragilisée).
            {!!weather.data.at_risk_refs.length && <span className="muted"> {weather.data.at_risk_refs.slice(0, 5).join(', ')}…</span>}
          </div>
          <a className="btn ghost" href="#/route">Planifier la tournée</a>
        </div>
      )}

      <div className="kpis">
        <Kpi icon="layers" label="Ouverts" value={s.open} hint={`${s.needs_review} à vérifier`} />
        <Kpi icon="alert" label="Urgents" value={s.urgent_open} hint="sévérité 4 ou 5" tone="critical" />
        <Kpi icon="clock" label="En retard" value={s.overdue} hint={`${s.warning} bientôt · ${s.escalated} escaladés`} tone="serious" />
        <Kpi icon="check" label="Réparés" value={s.fixed} hint={`${s.fix_verified} vérifiés par l’IA ou les citoyens`} tone="good" />
        <Kpi icon="wrench" label="Délai médian" value={ttf != null ? `${ttf} j` : '—'} hint={`p90 ${s.time_to_fix_days.p90 ?? '—'} j · du signalement à la réparation`} />
      </div>

      <div className="grid-2-1">
        <Card title="Signalements, confirmations et réparations par semaine" action={<Legend lines={LINES} />}>
          {trend.data ? <LineChart rows={trend.data} x="week" lines={LINES} label={weekLabel} /> : <Loading />}
        </Card>
        <Card title="Par statut">
          <Bars
            rows={(['new', 'confirmed', 'sheet_sent', 'reopened', 'fixed', 'rejected'] as const).map((k) => ({ label: STATUS[k].label, value: s.by_status[k] ?? 0 }))}
            tone={(i) => `tone-${STATUS[(['new', 'confirmed', 'sheet_sent', 'reopened', 'fixed', 'rejected'] as const)[i]].tone}`}
          />
          <div className="split">
            <div><span className="muted small">Fiches validées en</span><b>{s.sheet_approval_hours.median != null ? `${s.sheet_approval_hours.median} h` : '—'}</b></div>
            <div><span className="muted small">Faux positifs</span><b>{s.false_positive_rate != null ? `${Math.round(s.false_positive_rate * 100)} %` : '—'}</b></div>
            <div><span className="muted small">Exposés à la pluie</span><b>{s.rain_at_risk}</b></div>
          </div>
        </Card>
      </div>

      <div className="grid-2-1">
        <Card title="File prioritaire" action={<a className="link" href="#/queue">Tout voir →</a>}>
          <table className="table">
            <thead>
              <tr><th>Réf.</th><th>Adresse</th><th title="Survolez pour le détail">Priorité</th><th>Sévérité</th><th>Statut</th><th>Échéance</th></tr>
            </thead>
            <tbody>
              {queue.data?.items.map((p) => (
                <tr key={p.pothole_id} onClick={() => go('queue', p.pothole_id)} className="clickable">
                  <td className="mono">{p.ref}</td>
                  <td className="ellipsis">{p.address_label ?? '—'}</td>
                  <td><Priority p={p} /></td>
                  <td><Severity score={p.severity} /></td>
                  <td><StatusBadge status={p.status} /></td>
                  <td><Deadline p={p} /></td>
                </tr>
              ))}
              {queue.data && !queue.data.items.length && <tr><td colSpan={6} className="empty-row muted">Aucun nid-de-poule ouvert. 🎉</td></tr>}
            </tbody>
          </table>
        </Card>
        <Card title="Rues les plus abîmées" action={<span className="muted small" title="100 − 4 points par unité de sévérité ouverte">Indice de santé</span>}>
          {hot.data ? (
            <ul className="bars roads">
              {hot.data.roads.slice(0, 7).map((r) => (
                <li key={r.road}>
                  <span className="ellipsis" title={r.road}>{r.road}</span>
                  <span className="bar"><span className="fill" style={{ width: `${r.health}%`, background: healthColor(r.health) }} /></span>
                  <b>{r.health}</b>
                </li>
              ))}
            </ul>
          ) : <Loading />}
          <p className="muted small note">Plus l’indice est bas, plus la rue cumule de nids-de-poule ouverts et graves.</p>
        </Card>
      </div>
    </div>
  )
}

export const healthColor = (h: number) => (h >= 70 ? '#3E9E6B' : h >= 40 ? '#E0A21A' : '#C8322B')

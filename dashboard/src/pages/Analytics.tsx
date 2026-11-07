import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet'
import { api, type Group, type Office, usePoll } from '../api'
import { Bars, Legend, LineChart, SERIES, weekLabel } from '../components/charts'
import { ROAD_CLASS, SOURCE } from '../i18n'
import { Card, Icon, Kpi, Loading } from '../ui'
import { healthColor } from './Overview'

const LINES = [
  { key: 'reported', label: 'Signalés', color: SERIES.reported },
  { key: 'confirmed', label: 'Confirmés', color: SERIES.confirmed },
  { key: 'fixed', label: 'Réparés', color: SERIES.fixed },
]

/** Client-side CSV of what is on screen (the numbers match the cards). */
function downloadCsv(name: string, rows: (string | number | null)[][]) {
  const csv = '﻿' + rows.map((r) => r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })), download: name })
  a.click()
}

function TimeToFix({ title, groups, label = (k: string) => k }: { title: string; groups: Group[]; label?: (k: string) => string }) {
  return (
    <Card title={title} action={<span className="muted small">médiane (jours) · p90</span>}>
      {groups.length ? (
        <Bars rows={groups.slice(0, 8).map((g) => ({ label: label(g.key), value: g.median ?? 0, hint: `p90 ${g.p90 ?? '—'} j · ${g.n} réparés · ${g.open} ouverts` }))}
          format={(v) => (v ? `${v} j` : '—')} />
      ) : <p className="muted">Aucune réparation encore.</p>}
    </Card>
  )
}

export default function Analytics({ office }: { office: Office }) {
  const s = usePoll(() => api.summary(), 60000).data
  const trend = usePoll(() => api.trend(16), 60000).data
  const ttf = usePoll(api.timeToFix, 60000).data
  const hot = usePoll(api.hotspots, 60000).data
  const channels = usePoll(api.channels, 60000).data
  if (!s || !trend || !ttf || !hot || !channels) return <Loading />

  const exportView = () => downloadCsv(`sabeel-analyses-${office.code}.csv`, [
    ['indicateur', 'valeur'],
    ['ouverts', s.open], ['urgents', s.urgent_open], ['en retard', s.overdue], ['taux de retard', s.overdue_rate],
    ['réparés', s.fixed], ['délai médian (j)', s.time_to_fix_days.median], ['délai p90 (j)', s.time_to_fix_days.p90],
    ['validation fiche médiane (h)', s.sheet_approval_hours.median], ['taux de faux positifs', s.false_positive_rate],
    [], ['semaine', 'signalés', 'confirmés', 'réparés'], ...trend.map((w) => [w.week, w.reported, w.confirmed, w.fixed]),
    [], ['bureau', 'médiane (j)', 'p90 (j)', 'réparés', 'ouverts'], ...ttf.by_office.map((g) => [g.key, g.median, g.p90, g.n, g.open]),
    [], ['rue', 'commune', 'ouverts', 'indice de santé'], ...hot.roads.map((r) => [r.road, r.municipality, r.open, r.health]),
  ])

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Analyses</h1>
          <p className="muted">{office.is_ministry ? 'Tous les bureaux' : office.name} · indicateurs pour les décisions budgétaires</p>
        </div>
        <button className="btn ghost" onClick={exportView}><Icon name="download" size={15} /> Exporter la vue (CSV)</button>
      </header>

      <div className="kpis">
        <Kpi icon="wrench" label="Délai médian" value={s.time_to_fix_days.median != null ? `${s.time_to_fix_days.median} j` : '—'} hint={`p90 ${s.time_to_fix_days.p90 ?? '—'} j`} />
        <Kpi icon="clock" label="Taux de retard" value={s.overdue_rate != null ? `${Math.round(s.overdue_rate * 100)} %` : '—'} hint={`${s.overdue} en retard`} tone="serious" />
        <Kpi icon="file" label="Validation des fiches" value={s.sheet_approval_hours.median != null ? `${s.sheet_approval_hours.median} h` : '—'} hint="médiane, rédaction → approbation" />
        <Kpi icon="ban" label="Faux positifs" value={s.false_positive_rate != null ? `${Math.round(s.false_positive_rate * 100)} %` : '—'} hint="étiquettes « pas un nid-de-poule »" tone="critical" />
        <Kpi icon="alert" label="Escaladés" value={s.escalated} hint="échéance dépassée de 100 %" />
      </div>

      <Card title="Tendance hebdomadaire" action={<Legend lines={LINES} />}>
        <LineChart rows={trend} x="week" lines={LINES} label={weekLabel} />
      </Card>

      <div className="grid-3">
        <TimeToFix title="Délai de réparation par bureau" groups={ttf.by_office} />
        <TimeToFix title="Par gouvernorat" groups={ttf.by_region} />
        <TimeToFix title="Par type de route" groups={ttf.by_road_class} label={(k) => ROAD_CLASS[k] ?? k} />
      </div>

      <div className="grid-2-1">
        <Card title="Densité des nids-de-poule ouverts" className="flush">
          <MapContainer center={[36.822, 10.2]} zoom={11} className="map heat" preferCanvas>
            <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
            {hot.points.map(([lat, lon, w], i) => (
              <CircleMarker key={i} center={[lat, lon]} radius={10 + 14 * w} pathOptions={{ stroke: false, fillColor: '#C8322B', fillOpacity: 0.08 + 0.18 * w }} />
            ))}
          </MapContainer>
        </Card>
        <Card title="Canaux de signalement">
          <Bars rows={Object.entries(channels).map(([k, v]) => ({ label: SOURCE[k] ?? k, value: v }))} />
          <p className="muted small note">Application (photo), mode conduite (automatique) et page web sans installation.</p>
        </Card>
      </div>

      <Card title="Rues prioritaires pour le budget" className="flush">
        <table className="table">
          <thead><tr><th>Rue</th><th>Commune</th><th>Ouverts</th><th>Sévérité cumulée</th><th>Pire</th><th>Indice de santé</th></tr></thead>
          <tbody>
            {hot.roads.map((r) => (
              <tr key={r.road}>
                <td>{r.road}</td><td>{r.municipality ?? '—'}</td><td>{r.open}</td><td>{r.severity_sum}</td><td>{r.max_severity}/5</td>
                <td><span className="health" style={{ background: healthColor(r.health) }}>{r.health}</span></td>
              </tr>
            ))}
            {!hot.roads.length && <tr><td colSpan={6} className="empty-row muted">Aucun nid-de-poule ouvert.</td></tr>}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { go, OPEN, potholes, severityColor, type Report } from '../api'
import { Deadline, Icon, ReportPanel, Severity, StatusBadge } from '../ui'

const FILTERS = {
  open: { label: 'Ouverts', test: (r: Report) => OPEN.includes(r.status) },
  urgent: { label: 'Urgents', test: (r: Report) => OPEN.includes(r.status) && (r.score ?? 0) >= 4 },
  overdue: { label: 'En retard', test: (r: Report) => r.overdue },
  fixed: { label: 'Réparés', test: (r: Report) => r.status === 'fixed' },
  all: { label: 'Tous', test: () => true },
}
type Filter = keyof typeof FILTERS

function FlyTo({ r }: { r?: Report }) {
  const map = useMap()
  useEffect(() => {
    if (r) map.flyTo([r.lat, r.lon], Math.max(map.getZoom(), 16), { duration: 0.6 })
  }, [r, map])
  return null
}

export default function MapPage({ reports, focus, onChanged }: { reports: Report[] | null; focus?: string; onChanged: () => void }) {
  const [filter, setFilter] = useState<Filter>('open')
  const all = useMemo(() => potholes(reports ?? []), [reports])
  const shown = all.filter(FILTERS[filter].test).sort((a, b) => b.priority - a.priority)
  // A focus id may be any report of a cluster (e.g. from the assistant): show its pothole.
  const focused = reports?.find((r) => r.report_id === focus)
  const selected = focused && all.find((p) => (p.cluster_id ?? p.report_id) === (focused.cluster_id ?? focused.report_id))

  if (!reports) return <div className="loading">Chargement…</div>
  return (
    <div className="map-page">
      <div className="map-wrap">
        <div className="map-toolbar">
          {(Object.keys(FILTERS) as Filter[]).map((f) => (
            <button key={f} className={f === filter ? 'chip active' : 'chip'} onClick={() => setFilter(f)}>
              {FILTERS[f].label} <span>{all.filter(FILTERS[f].test).length}</span>
            </button>
          ))}
        </div>
        <MapContainer center={[36.822, 10.2]} zoom={12} className="map" zoomControl={false}>
          <TileLayer
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />
          {(selected && !shown.includes(selected) ? [...shown, selected] : shown).map((r) => (
            <CircleMarker
              key={r.report_id}
              center={[r.lat, r.lon]}
              radius={7 + Math.min(r.cluster_size, 5) * 1.6}
              pathOptions={{
                color: r.report_id === selected?.report_id ? '#1D2023' : '#fff',
                weight: r.report_id === selected?.report_id ? 3 : 2,
                fillColor: r.status === 'fixed' ? '#1A9E8F' : severityColor(r.score),
                fillOpacity: 0.92,
              }}
              eventHandlers={{ click: () => go('map', r.report_id) }}
            >
              <Tooltip direction="top" offset={[0, -8]}>
                <b>{r.ref}</b> · {r.address ?? 'Adresse inconnue'}
              </Tooltip>
            </CircleMarker>
          ))}
          <FlyTo r={selected} />
        </MapContainer>
        <div className="map-legend">
          {[5, 4, 3, 1].map((s) => (
            <span key={s}><i style={{ background: severityColor(s) }} />{s === 1 ? '1–2' : s}</span>
          ))}
          <span><i style={{ background: severityColor(null) }} />À évaluer</span>
          <span><i style={{ background: '#1A9E8F' }} />Réparé</span>
          <span className="muted">Taille = nb de citoyens</span>
        </div>
      </div>

      {selected ? (
        <ReportPanel r={selected} onClose={() => go('map')} onChanged={onChanged} />
      ) : (
        <aside className="panel list-panel">
          <header className="panel-head">
            <div>
              <div className="ref">{FILTERS[filter].label}</div>
              <h3>{shown.length} nids-de-poule</h3>
            </div>
          </header>
          <ul className="pothole-list">
            {shown.map((r) => (
              <li key={r.report_id} onClick={() => go('map', r.report_id)}>
                <span className="dot-lg" style={{ background: r.status === 'fixed' ? '#1A9E8F' : severityColor(r.score) }} />
                <div className="grow">
                  <div className="row-between">
                    <b className="mono">{r.ref}</b>
                    <Deadline r={r} />
                  </div>
                  <div className="ellipsis">{r.address ?? '—'}</div>
                  <div className="row-between">
                    <StatusBadge status={r.status} />
                    <Severity score={r.score} />
                  </div>
                </div>
              </li>
            ))}
            {!shown.length && <li className="muted"><Icon name="check" /> Rien à afficher pour ce filtre.</li>}
          </ul>
        </aside>
      )}
    </div>
  )
}

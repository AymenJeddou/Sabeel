import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { api, FIXED_COLOR, go, type Pothole, severityColor, usePoll } from '../api'
import PotholePanel from '../components/PotholePanel'
import { Deadline, Icon, Loading, Severity, StatusBadge } from '../ui'

const OPEN = ['new', 'confirmed', 'sheet_sent', 'reopened']
const FILTERS = {
  open: { label: 'Ouverts', test: (p: Pothole) => OPEN.includes(p.status) },
  urgent: { label: 'Urgents', test: (p: Pothole) => OPEN.includes(p.status) && (p.severity ?? 0) >= 4 },
  overdue: { label: 'En retard', test: (p: Pothole) => p.overdue },
  review: { label: 'À vérifier', test: (p: Pothole) => p.needs_review && OPEN.includes(p.status) },
  fixed: { label: 'Réparés', test: (p: Pothole) => p.status === 'fixed' },
  all: { label: 'Tous', test: (p: Pothole) => p.status !== 'rejected' },
}
type Filter = keyof typeof FILTERS
const color = (p: Pothole) => (p.status === 'fixed' ? FIXED_COLOR : severityColor(p.severity))

function FlyTo({ p }: { p?: Pothole }) {
  const map = useMap()
  useEffect(() => {
    if (p) map.flyTo([p.lat, p.lon], Math.max(map.getZoom(), 16), { duration: 0.6 })
  }, [p, map])
  return null
}

/** Every pothole of the office on one map (canvas renderer: smooth with 5,000+ points). */
export default function MapPage({ focus, onChanged, version }: { focus?: string; onChanged: () => void; version: number }) {
  const [filter, setFilter] = useState<Filter>('open')
  const { data, refresh } = usePoll(() => api.queue({ status: 'any', limit: 500, sort: 'priority' }).then(async (first) => {
    // Pull every page so the map shows the whole office (the queue is paged by 500).
    const items = [...first.items]
    for (let c = first.next_cursor; c != null && items.length < 20000;) {
      const next = await api.queue({ status: 'any', limit: 500, cursor: c })
      items.push(...next.items)
      c = next.next_cursor
    }
    return items
  }), 60000, [version])
  const all = useMemo(() => data ?? [], [data])
  const shown = all.filter(FILTERS[filter].test)
  const selected = all.find((p) => p.pothole_id === focus)

  if (!data) return <Loading />
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
        <MapContainer center={[36.822, 10.2]} zoom={12} className="map" zoomControl={false} preferCanvas>
          <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' />
          {(selected && !shown.includes(selected) ? [...shown, selected] : shown).map((p) => (
            <CircleMarker
              key={p.pothole_id}
              center={[p.lat, p.lon]}
              radius={6 + Math.min(p.device_count, 5) * 1.5}
              pathOptions={{
                color: p.pothole_id === focus ? '#1D2023' : p.needs_review ? '#B7791F' : '#fff',
                weight: p.pothole_id === focus ? 3 : 2,
                fillColor: color(p),
                fillOpacity: p.status === 'fixed' ? 0.55 : 0.92,
                dashArray: p.needs_review ? '3 3' : undefined,
              }}
              eventHandlers={{ click: () => go('map', p.pothole_id) }}
            >
              <Tooltip direction="top" offset={[0, -8]}><b>{p.ref}</b> · {p.address_label ?? 'Adresse inconnue'}</Tooltip>
            </CircleMarker>
          ))}
          <FlyTo p={selected} />
        </MapContainer>
        <div className="map-legend">
          {[5, 4, 3, 1].map((s) => <span key={s}><i style={{ background: severityColor(s) }} />{s === 1 ? '1–2' : s}</span>)}
          <span><i style={{ background: severityColor(null) }} />À évaluer</span>
          <span><i style={{ background: FIXED_COLOR }} />Réparé</span>
          <span className="muted">Taille = nb de citoyens · pointillés = à vérifier</span>
        </div>
      </div>

      {focus ? (
        <PotholePanel id={focus} onClose={() => go('map')} onChanged={() => (refresh(), onChanged())} />
      ) : (
        <aside className="panel list-panel">
          <header className="panel-head">
            <div><div className="ref">{FILTERS[filter].label}</div><h3>{shown.length} nids-de-poule</h3></div>
          </header>
          <ul className="pothole-list">
            {shown.slice(0, 200).map((p) => (
              <li key={p.pothole_id} onClick={() => go('map', p.pothole_id)}>
                <span className="dot-lg" style={{ background: color(p) }} />
                <div className="grow">
                  <div className="row-between"><b className="mono">{p.ref}</b><Deadline p={p} /></div>
                  <div className="ellipsis">{p.address_label ?? '—'}</div>
                  <div className="row-between"><StatusBadge status={p.status} /><Severity score={p.severity} /></div>
                </div>
              </li>
            ))}
            {shown.length > 200 && <li className="muted small">… et {shown.length - 200} autres (zoomez sur la carte).</li>}
            {!shown.length && <li className="muted"><Icon name="check" /> Rien à afficher pour ce filtre.</li>}
          </ul>
        </aside>
      )}
    </div>
  )
}

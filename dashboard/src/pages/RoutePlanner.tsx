import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { latLngBounds } from 'leaflet'
import { api, go, type Office, type RoutePlan, severityColor } from '../api'
import { ErrorNote, Icon, Loading, Priority, Severity } from '../ui'

function Fit({ plan }: { plan: RoutePlan }) {
  const map = useMap()
  useEffect(() => {
    const pts: [number, number][] = [[plan.start.lat, plan.start.lon], ...plan.stops.map((s) => [s.lat, s.lon] as [number, number])]
    if (pts.length > 1) map.fitBounds(latLngBounds(pts), { padding: [40, 40] })
  }, [plan, map])
  return null
}

/** "Today's tour": the highest-priority potholes in a driving order (OSRM). */
export default function RoutePlanner({ office }: { office: Office }) {
  const [stops, setStops] = useState(8)
  const [minSev, setMinSev] = useState(3)
  const [start, setStart] = useState<{ lat: number; lon: number } | null>(null)
  const [plan, setPlan] = useState<RoutePlan | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const build = async () => {
    setBusy(true)
    setError(null)
    try {
      setPlan(await api.route({ max_stops: stops, min_severity: minSev, start_lat: start?.lat, start_lon: start?.lon }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }
  useEffect(() => { void build() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const here = () => navigator.geolocation.getCurrentPosition(
    (p) => setStart({ lat: p.coords.latitude, lon: p.coords.longitude }),
    () => setError('Position indisponible : départ depuis le bureau.'),
  )
  const gmaps = plan && plan.stops.length
    ? `https://www.google.com/maps/dir/${[plan.start, ...plan.stops].map((s) => `${s.lat},${s.lon}`).join('/')}`
    : null

  return (
    <div className="map-page">
      <div className="map-wrap">
        {!plan ? <Loading /> : (
          <MapContainer center={[office.lat ?? 36.8, office.lon ?? 10.18]} zoom={12} className="map" zoomControl={false}>
            <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap · itinéraire OSRM" />
            {plan.geometry && <Polyline positions={plan.geometry.coordinates.map(([lon, lat]) => [lat, lon] as [number, number])} pathOptions={{ color: '#1B4F8F', weight: 5, opacity: 0.8 }} />}
            <CircleMarker center={[plan.start.lat, plan.start.lon]} radius={9} pathOptions={{ color: '#fff', weight: 3, fillColor: '#12304F', fillOpacity: 1 }}>
              <Tooltip permanent direction="top" offset={[0, -10]}>Départ</Tooltip>
            </CircleMarker>
            {plan.stops.map((s) => (
              <CircleMarker key={s.pothole_id} center={[s.lat, s.lon]} radius={11} eventHandlers={{ click: () => go('queue', s.pothole_id) }}
                pathOptions={{ color: '#fff', weight: 2, fillColor: severityColor(s.severity), fillOpacity: 0.95 }}>
                <Tooltip permanent direction="center" className="stop-label">{s.stop}</Tooltip>
              </CircleMarker>
            ))}
            <Fit plan={plan} />
          </MapContainer>
        )}
      </div>

      <aside className="panel">
        <header className="panel-head">
          <div><div className="ref">Tournée du jour</div><h3>{plan ? `${plan.stops.length} arrêts · ${plan.distance_km} km · ~${plan.duration_min} min` : 'Calcul…'}</h3></div>
        </header>
        <div className="panel-body">
          <div className="toolbar">
            <label className="field inline">Arrêts
              <input type="number" min={1} max={25} value={stops} onChange={(e) => setStops(Number(e.target.value))} />
            </label>
            <label className="field inline">Sévérité min.
              <select value={minSev} onChange={(e) => setMinSev(Number(e.target.value))}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select>
            </label>
          </div>
          <div className="toolbar">
            <button className="btn ghost" onClick={here}><Icon name="pin" size={15} /> {start ? 'Départ : ma position' : 'Partir de ma position'}</button>
            <button className="btn primary" disabled={busy} onClick={build}><Icon name="route" size={15} /> Recalculer</button>
          </div>
          {plan?.engine === 'fallback' && <p className="notice warn small">Calcul hors ligne (OSRM indisponible) : ordre optimisé à vol d’oiseau, distances estimées.</p>}
          <ErrorNote error={error} />
          <ol className="stops">
            {plan?.stops.map((s) => (
              <li key={s.pothole_id} onClick={() => go('queue', s.pothole_id)}>
                <span className="stop-num" style={{ background: severityColor(s.severity) }}>{s.stop}</span>
                <div className="grow">
                  <div className="row-between"><b className="mono">{s.ref}</b><Priority p={s} /></div>
                  <div className="ellipsis">{s.address_label ?? '—'}</div>
                  <div className="row-between"><Severity score={s.severity} /><span className="muted small">{s.method?.split(':')[0]}</span></div>
                </div>
              </li>
            ))}
            {plan && !plan.stops.length && <li className="muted">Aucun nid-de-poule confirmé à cette sévérité.</li>}
          </ol>
        </div>
        <footer className="panel-actions">
          <button className="btn ghost" onClick={() => print()}><Icon name="file" size={15} /> Imprimer</button>
          {gmaps && <a className="btn primary" href={gmaps} target="_blank" rel="noreferrer"><Icon name="external" size={15} /> Ouvrir le GPS</a>}
        </footer>
      </aside>
    </div>
  )
}

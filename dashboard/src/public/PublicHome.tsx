import { useState } from 'react'
import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet'
import { api, FIXED_COLOR, severityColor, usePoll } from '../api'
import { Legend, LineChart, monthLabel, SERIES } from '../components/charts'
import { STATUS } from '../i18n'
import { Card, Icon, Loading, Mark, Severity } from '../ui'

const LINES = [
  { key: 'reported', label: 'Signalés', color: SERIES.reported },
  { key: 'fixed', label: 'Réparés', color: SERIES.fixed },
]

/** Public transparency page (issue #30): proof that reporting works. Aggregate only. */
export default function PublicHome({ focus }: { focus?: string }) {
  const [state, setState] = useState<'open' | 'fixed'>('open')
  const stats = usePoll(api.publicStats, 300000).data
  const points = usePoll(() => api.publicMap(state), 300000, [state]).data
  const card = usePoll(() => (focus ? api.publicPothole(focus) : Promise.resolve(null)), 0, [focus]).data

  return (
    <div className="public">
      <header className="public-head">
        <a href="#/" className="brand-inline"><Mark size={34} /><b>Sabeel</b><span className="muted small">سبيل · la voie</span></a>
        <nav className="toolbar">
          <a className="btn ghost" href="#/track">Mes signalements</a>
          <a className="btn ghost" href="#/overview">Espace autorités</a>
        </nav>
      </header>

      <section className="hero">
        <div>
          <h1>Un nid-de-poule ? Une photo suffit.</h1>
          <p>Sabeel localise et évalue le nid-de-poule, l’envoie au service compétent avec la règle de droit applicable, et vous montre quand il est réparé.</p>
          <div className="toolbar">
            <a className="btn primary big" href="#/report"><Icon name="camera" size={18} /> Signaler maintenant</a>
            <a className="btn ghost big" href="https://github.com/AymenJeddou/Sabeel/releases" target="_blank" rel="noreferrer"><Icon name="download" size={18} /> Application Android</a>
          </div>
          <p className="muted small">Sans compte · photos floutées · données ouvertes et agrégées.</p>
        </div>
        {stats ? (
          <div className="counters">
            <div><b>{stats.reported}</b><span>signalés</span></div>
            <div><b>{stats.fixed}</b><span>réparés</span></div>
            <div><b>{stats.median_days_to_fix ?? '—'}</b><span>jours (délai médian)</span></div>
            <div><b>{stats.fixed_last_30_days}</b><span>réparés ce mois-ci</span></div>
            <div><b>{stats.fix_verified}</b><span>réparations vérifiées</span></div>
            <div><b>{stats.citizens_confirmations}</b><span>« je le vois aussi »</span></div>
          </div>
        ) : <Loading />}
      </section>

      {card && (
        <Card title={`Nid-de-poule ${card.ref}`} className="public-card">
          <p>{card.address_label ?? '—'} · <Severity score={card.severity} /> · {STATUS[card.status].label}{card.fix_verified ? ' · réparation vérifiée' : ''}</p>
          <p className="muted small">Signalé le {card.created_on}{card.fixed_on ? ` · réparé le ${card.fixed_on}` : ''} · {card.report_count} signalement(s) · {card.target_office ?? ''}</p>
        </Card>
      )}

      <div className="public-grid">
        <Card title="Carte" action={
          <span className="toolbar">
            <button className={state === 'open' ? 'chip active' : 'chip'} onClick={() => setState('open')}>Ouverts</button>
            <button className={state === 'fixed' ? 'chip active' : 'chip'} onClick={() => setState('fixed')}>Réparés</button>
          </span>
        } className="flush">
          <MapContainer center={[36.822, 10.2]} zoom={11} className="map public-map" preferCanvas>
            <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
            {points?.map((p, i) => (
              <CircleMarker key={i} center={[p.lat, p.lon]} radius={6}
                pathOptions={{ color: '#fff', weight: 1.5, fillColor: p.status === 'fixed' ? FIXED_COLOR : severityColor(p.severity), fillOpacity: 0.9 }} />
            ))}
          </MapContainer>
        </Card>
        <Card title="Chaque mois" action={<Legend lines={LINES} />}>
          {stats ? <LineChart rows={stats.monthly} x="month" lines={LINES} label={monthLabel} height={200} /> : <Loading />}
        </Card>
      </div>

      {stats && (
        <div className="public-grid">
          <Card title="Par gouvernorat" className="flush">
            <table className="table">
              <thead><tr><th>Gouvernorat</th><th>Signalés</th><th>Réparés</th><th>Délai médian</th></tr></thead>
              <tbody>
                {stats.regions.map((r) => (
                  <tr key={r.region}>
                    <td>{r.region}</td>
                    {r.suppressed ? <td colSpan={3} className="muted small">moins de 5 nids-de-poule (masqué)</td> : <>
                      <td>{r.reported}</td><td>{r.fixed}</td><td>{r.median_days_to_fix != null ? `${r.median_days_to_fix} j` : '—'}</td>
                    </>}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <Card title="Rues les plus abîmées">
            <ul className="bars roads">
              {stats.worst_roads.map((r) => (
                <li key={r.road}><span className="ellipsis">{r.road}</span><span className="muted small">{r.open} ouvert(s)</span><b>{r.health}/100</b></li>
              ))}
            </ul>
            <p className="muted small note">Indice de santé : 100 − 4 points par unité de sévérité ouverte.</p>
          </Card>
        </div>
      )}

      <footer className="public-foot muted small">
        Sabeel · projet fédérateur, Tunisie · Données © OpenStreetMap · Aucun compte, aucune donnée personnelle (loi 2004-63).
      </footer>
    </div>
  )
}

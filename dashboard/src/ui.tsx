import { useState, type ReactNode } from 'react'
import { api, ago, date, NEXT, severityColor, STATUS, type Report, type Status } from './api'

const PIN = 'M100 250C64 196 20 152 20 100a80 80 0 0 1 160 0c0 52-44 96-80 150z'
const ROAD = 'M44 206c0-74 110-64 110-114 0-34-28-56-58-66'

/** The Sabeel mark (same paths as mobile/lib/app/brand.dart). */
export const Mark = ({ size = 32, color = 'var(--navy)' }: { size?: number; color?: string }) => (
  <svg width={(size * 200) / 260} height={size} viewBox="0 0 200 260" aria-hidden>
    <clipPath id="mark-clip"><path d={PIN} /></clipPath>
    <path d={PIN} fill={color} />
    <g clipPath="url(#mark-clip)" fill="none">
      <path d={ROAD} stroke="#fff" strokeWidth="28" />
      <path d={ROAD} stroke="var(--amber)" strokeWidth="4" strokeDasharray="11 9" />
    </g>
  </svg>
)

// Stroke icons, 24x24 viewBox, drawn in the Lucide style.
const ICONS = {
  grid: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z',
  map: 'M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  chat: 'M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z',
  spark: 'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 16l.8 2.2 2.2.8-2.2.8L19 22l-.8-2.2-2.2-.8 2.2-.8z',
  x: 'M18 6 6 18M6 6l12 12',
  pin: 'M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2',
  alert: 'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01',
  check: 'M20 6 9 17l-5-5',
  send: 'M22 2 11 13M22 2l-7 20-4-9-9-4z',
  download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  external: 'M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6',
  layers: 'M12 2 2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 13h6M9 17h6',
  wrench: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z',
  ban: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM4.9 4.9l14.2 14.2',
  car: 'M5 17h14M6 17v2M18 17v2M3 13l2-6h14l2 6v4H3zM7 13h.01M17 13h.01',
  hand: 'M18 11V6a2 2 0 0 0-4 0M14 10V4a2 2 0 0 0-4 0v2M10 10.5V6a2 2 0 0 0-4 0v8M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.9-6-2.4l-3.6-3.6a2 2 0 0 1 2.8-2.8L7 15',
} as const
export type IconName = keyof typeof ICONS

export const Icon = ({ name, size = 18 }: { name: IconName; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden className="icon">
    <path d={ICONS[name]} />
  </svg>
)

const STATUS_ICON: Record<Status, IconName> = { new: 'spark', confirmed: 'users', sheet_sent: 'file', fixed: 'check', rejected: 'ban' }

export const StatusBadge = ({ status }: { status: Status }) => (
  <span className={`badge tone-${STATUS[status].tone}`}>
    <Icon name={STATUS_ICON[status]} size={12} /> {STATUS[status].label}
  </span>
)

/** Five pips, filled up to the score, in the severity colour; "À évaluer" when the model saw nothing. */
export const Severity = ({ score }: { score: number | null }) =>
  score == null ? (
    <span className="muted small">À évaluer</span>
  ) : (
    <span className="severity" title={`Sévérité ${score}/5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <i key={i} style={{ background: i <= score ? severityColor(score) : undefined }} />
      ))}
      <b>{score}</b>
    </span>
  )

/** "dans 3 jours" / "en retard de 5 jours" against the severity deadline. */
export function Deadline({ r }: { r: Report }) {
  if (!r.due_at || r.status === 'fixed' || r.status === 'rejected') return <span className="muted">—</span>
  return (
    <span className={r.overdue ? 'deadline late' : 'deadline'}>
      <Icon name={r.overdue ? 'alert' : 'clock'} size={13} /> {r.overdue ? `En retard · ${ago(r.due_at).replace('il y a ', '')}` : ago(r.due_at)}
    </span>
  )
}

export const Card = ({ title, action, children, className = '' }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) => (
  <section className={`card ${className}`}>
    {title && (
      <header className="card-head">
        <h2>{title}</h2>
        {action}
      </header>
    )}
    {children}
  </section>
)

const ACTION_LABEL: Record<Status, string> = {
  new: '', confirmed: 'Confirmer', sheet_sent: 'Marquer fiche envoyée', fixed: 'Marquer réparé', rejected: 'Rejeter',
}

/** Everything about one pothole plus the actions an agent can take on it. */
export function ReportPanel({ r, onClose, onChanged, onShowOnMap }: {
  r: Report
  onClose: () => void
  onChanged: () => void
  onShowOnMap?: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const next = NEXT[r.status]
  const canReject = ['new', 'confirmed', 'sheet_sent'].includes(r.status)

  const move = async (to: Status) => {
    if (to === 'rejected' && !confirm(`Rejeter ${r.ref} comme faux positif ?`)) return
    setBusy(true)
    setError(null)
    try {
      await api.setStatus(r.report_id, to)
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside className="panel">
      <header className="panel-head">
        <div>
          <div className="ref">{r.ref}</div>
          <h3>{r.address ?? 'Adresse inconnue'}</h3>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Fermer"><Icon name="x" /></button>
      </header>
      {r.photo_url && <img className="panel-photo" src={r.photo_url} alt={`Photo du signalement ${r.ref}`} />}
      <div className="panel-body">
        <div className="panel-row"><StatusBadge status={r.status} /><Severity score={r.score} /></div>
        <dl className="facts">
          <dt>Signalements</dt><dd>{r.cluster_size} citoyen{r.cluster_size > 1 ? 's' : ''}</dd>
          <dt>Premier signalement</dt><dd>{date(r.created_at)}</dd>
          <dt>Échéance</dt><dd><Deadline r={r} /></dd>
          <dt>Service</dt><dd>{r.target_office === 'Municipality' ? 'Municipalité' : r.target_office ?? 'Non attribué'}</dd>
          <dt>Confiance IA</dt><dd>{r.confidence != null ? `${Math.round(r.confidence * 100)} %` : '—'}</dd>
          <dt>Source</dt><dd><Icon name={r.source === 'driving_mode' ? 'car' : 'hand'} size={13} /> {r.source === 'driving_mode' ? 'Mode conduite' : 'Manuel'}</dd>
          <dt>GPS</dt>
          <dd className="mono">
            {r.lat.toFixed(5)}, {r.lon.toFixed(5)}{' '}
            <a href={`https://www.google.com/maps/dir/?api=1&destination=${r.lat},${r.lon}`} target="_blank" rel="noreferrer" title="Itinéraire">
              <Icon name="external" size={13} />
            </a>
          </dd>
        </dl>
        {r.sheet_text && (
          <details className="sheet">
            <summary><Icon name="file" size={14} /> Fiche d'intervention</summary>
            <pre>{r.sheet_text}</pre>
          </details>
        )}
        {error && <p className="error">{error}</p>}
      </div>
      <footer className="panel-actions">
        {onShowOnMap && <button className="btn ghost" onClick={onShowOnMap}><Icon name="map" size={15} /> Carte</button>}
        {canReject && <button className="btn ghost danger" disabled={busy} onClick={() => move('rejected')}><Icon name="ban" size={15} /> Rejeter</button>}
        {next && <button className="btn primary" disabled={busy} onClick={() => move(next)}><Icon name={STATUS_ICON[next]} size={15} /> {ACTION_LABEL[next]}</button>}
      </footer>
    </aside>
  )
}

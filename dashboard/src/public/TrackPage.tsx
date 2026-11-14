import type { ReactNode } from 'react'
import { api, date, usePoll } from '../api'
import { STATUS } from '../i18n'
import { ErrorNote, Icon, Loading, Mark, Severity } from '../ui'
import { myReports } from './report'

const STEPS = [
  { status: 'new', label: 'Reçu' },
  { status: 'confirmed', label: 'Confirmé' },
  { status: 'sheet_sent', label: 'Transmis' },
  { status: 'fixed', label: 'Réparé' },
] as const

/** The 4-step tracker for one report, polled every 30 s (no account needed:
 * the random device_report_id in the URL is the proof). */
export default function TrackPage({ id }: { id?: string }) {
  if (!id) return <MyReports />
  return <Tracker id={id} />
}

function Tracker({ id }: { id: string }) {
  const { data: r, error } = usePoll(() => api.track(id), 30000, [id])
  if (error && !r) return <Shell><ErrorNote error={error.includes('Unknown') ? 'Signalement introuvable (pas encore envoyé ?).' : error} /></Shell>
  if (!r) return <Shell><Loading /></Shell>
  const reached = (s: string) => r.timeline.find((t) => t.status === s)
  const current = STEPS.findIndex((s) => s.status === r.status)

  return (
    <Shell>
      <div className="row-between">
        <div><div className="ref">Signalement</div><h2 className="mono">{r.ref ?? '—'}</h2></div>
        <Severity score={r.severity} />
      </div>
      <p className="muted">{r.address_label ?? 'Adresse en cours d’identification'}{r.target_office ? ` · ${r.target_office}` : ''}</p>
      {r.status === 'rejected' && <p className="notice warn">Après vérification, ce signalement n’est pas un nid-de-poule. Merci quand même !</p>}
      {r.status === 'reopened' && <p className="notice critical">Des citoyens indiquent qu’il est toujours là : le dossier est rouvert en priorité.</p>}
      {!r.detected && r.status === 'new' && <p className="notice warn">En attente de vérification par un agent.</p>}
      <ol className="tracker">
        {STEPS.map((s, i) => {
          const done = reached(s.status) || (current >= i && current !== -1)
          return (
            <li key={s.status} className={done ? 'done' : ''}>
              <span className="step-dot">{done ? <Icon name="check" size={14} /> : i + 1}</span>
              <div>
                <b>{s.label}</b>
                <span className="muted small">{reached(s.status) ? date(reached(s.status)!.at) : ''}</span>
              </div>
            </li>
          )
        })}
      </ol>
      {r.sheet_summary && <pre className="sheet-summary">{r.sheet_summary}</pre>}
      <p className="muted small">Statut actuel : {STATUS[r.status].label} · actualisé automatiquement.</p>
    </Shell>
  )
}

function MyReports() {
  const ids = myReports()
  return (
    <Shell>
      <h2>Mes signalements</h2>
      {!ids.length && <p className="muted">Aucun signalement envoyé depuis ce navigateur.</p>}
      <ul className="link-list">{ids.map((id) => <li key={id}><a href={`#/track/${id}`}>{id.slice(0, 8)}…</a></li>)}</ul>
    </Shell>
  )
}

const Shell = ({ children }: { children: ReactNode }) => (
  <div className="public report-page">
    <header className="public-head">
      <a href="#/" className="brand-inline"><Mark size={30} /><b>Sabeel</b></a>
      <a className="btn ghost" href="#/report"><Icon name="camera" size={15} /> Signaler</a>
    </header>
    <main className="report-card">{children}</main>
  </div>
)

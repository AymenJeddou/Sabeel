import { useState } from 'react'
import { api, go, qs, type QueueFilters, usePoll } from '../api'
import PotholePanel from '../components/PotholePanel'
import { ROAD_CLASS } from '../i18n'
import { Deadline, ErrorNote, Icon, Loading, Priority, Severity, SheetBadge, StatusBadge } from '../ui'

const VIEWS: Record<string, { label: string; f: QueueFilters }> = {
  open: { label: 'Ouverts', f: { status: 'open' } },
  review: { label: 'À vérifier', f: { status: 'open', needs_review: true } },
  sheets: { label: 'Fiches à valider', f: { status: 'open', sheet_status: 'generated' } },
  overdue: { label: 'En retard', f: { status: 'open', overdue: true } },
  urgent: { label: 'Urgents', f: { status: 'open', sev: '4,5' } },
  fixed: { label: 'Réparés', f: { status: 'fixed' } },
  rejected: { label: 'Rejetés', f: { status: 'rejected' } },
}
const PAGE = 50

/** The office's to-do list: sorted by priority, filterable, exportable. */
export default function Queue({ focus, onChanged, version }: { focus?: string; onChanged: () => void; version: number }) {
  const [view, setView] = useState('open')
  const [sort, setSort] = useState('priority')
  const [region, setRegion] = useState('')
  const [cursor, setCursor] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const filters: QueueFilters = { ...VIEWS[view].f, sort, region: region || undefined }
  const queue = usePoll(() => api.queue({ ...filters, limit: PAGE, cursor }), 20000, [view, sort, region, cursor, version])
  const regions = [...new Set(queue.data?.items.map((p) => p.region).filter(Boolean) as string[])]

  const exportAs = (format: 'csv' | 'geojson') => {
    const { limit: _l, cursor: _c, ...f } = filters
    void _l; void _c
    api.download(`/export${qs({ format, ...f })}`, `sabeel-${view}.${format}`).catch((e) => setError(e.message))
  }

  return (
    <div className={focus ? 'page with-panel' : 'page'}>
      <div className="page-main">
        <header className="page-head">
          <div>
            <h1>File de travail</h1>
            <p className="muted">Triée par priorité : survolez le score pour voir pourquoi.</p>
          </div>
          <div className="toolbar">
            <button className="btn ghost" onClick={() => exportAs('csv')}><Icon name="download" size={15} /> CSV</button>
            <button className="btn ghost" onClick={() => exportAs('geojson')}><Icon name="download" size={15} /> GeoJSON</button>
          </div>
        </header>
        <div className="toolbar">
          {Object.entries(VIEWS).map(([k, v]) => (
            <button key={k} className={k === view ? 'chip active' : 'chip'} onClick={() => (setView(k), setCursor(0))}>{v.label}</button>
          ))}
          <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Trier par">
            <option value="priority">Priorité</option>
            <option value="deadline">Échéance</option>
            <option value="severity">Sévérité</option>
            <option value="age">Ancienneté</option>
          </select>
          {regions.length > 1 && (
            <select value={region} onChange={(e) => setRegion(e.target.value)} aria-label="Gouvernorat">
              <option value="">Tous les gouvernorats</option>
              {regions.map((r) => <option key={r}>{r}</option>)}
            </select>
          )}
        </div>
        <ErrorNote error={error ?? queue.error} />
        <section className="card flush">
          {!queue.data ? <Loading /> : (
            <table className="table">
              <thead>
                <tr><th>Réf.</th><th>Adresse</th><th>Priorité</th><th>Sévérité</th><th>Statut</th><th className="opt">Fiche</th><th className="opt">Route</th><th className="opt">Citoyens</th><th>Échéance</th></tr>
              </thead>
              <tbody>
                {queue.data.items.map((p) => (
                  <tr key={p.pothole_id} className={p.pothole_id === focus ? 'clickable selected' : 'clickable'} onClick={() => go('queue', p.pothole_id)}>
                    <td className="mono">{p.ref}{p.needs_review && <span className="dot-warn" title="À vérifier" />}</td>
                    <td className="ellipsis" title={p.address_label ?? ''}>{p.address_label ?? '—'}</td>
                    <td><Priority p={p} /></td>
                    <td><Severity score={p.severity} /></td>
                    <td><StatusBadge status={p.status} /></td>
                    <td className="opt"><SheetBadge status={p.sheet_status} /></td>
                    <td className="small opt">{p.road_ref ?? ROAD_CLASS[p.road_class ?? ''] ?? '—'}</td>
                    <td className="opt">{p.device_count}</td>
                    <td><Deadline p={p} /></td>
                  </tr>
                ))}
                {!queue.data.items.length && <tr><td colSpan={9} className="empty-row muted">Rien dans cette vue.</td></tr>}
              </tbody>
            </table>
          )}
        </section>
        {queue.data && queue.data.total > PAGE && (
          <div className="toolbar pager">
            <button className="btn ghost" disabled={!cursor} onClick={() => setCursor(Math.max(0, cursor - PAGE))}>← Précédent</button>
            <span className="muted">{cursor + 1}–{Math.min(cursor + PAGE, queue.data.total)} sur {queue.data.total}</span>
            <button className="btn ghost" disabled={queue.data.next_cursor == null} onClick={() => setCursor(queue.data!.next_cursor ?? cursor)}>Suivant →</button>
          </div>
        )}
      </div>
      {focus && (
        <PotholePanel id={focus} onClose={() => go('queue')} onChanged={() => (queue.refresh(), onChanged())} onShowOnMap={() => go('map', focus)} />
      )}
    </div>
  )
}

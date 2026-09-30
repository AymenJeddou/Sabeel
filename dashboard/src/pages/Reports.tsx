import { useMemo, useState } from 'react'
import { date, go, potholes, STATUS, type Report, type Status } from '../api'
import { Deadline, Icon, ReportPanel, Severity, StatusBadge } from '../ui'

type Sort = 'priority' | 'created_at' | 'score' | 'cluster_size'
const SORTS: Record<Sort, string> = { priority: 'Priorité', created_at: 'Date', score: 'Sévérité', cluster_size: 'Citoyens' }

function exportCsv(rows: Report[]) {
  const cols = ['ref', 'address', 'lat', 'lon', 'score', 'status', 'cluster_size', 'target_office', 'created_at', 'due_at', 'overdue'] as const
  const cell = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const csv = [cols.join(';'), ...rows.map((r) => cols.map((c) => cell(r[c])).join(';'))].join('\n')
  const a = document.createElement('a')
  // BOM so Excel opens the accents correctly.
  a.href = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }))
  a.download = `sabeel-signalements-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

export default function Reports({ reports, focus, onChanged }: { reports: Report[] | null; focus?: string; onChanged: () => void }) {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState<Status | ''>('')
  const [sort, setSort] = useState<Sort>('priority')
  const [each, setEach] = useState(false)

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (each ? reports ?? [] : potholes(reports ?? []))
      .filter((r) => !status || r.status === status)
      .filter((r) => !needle || `${r.ref} ${r.address ?? ''} ${r.target_office ?? ''}`.toLowerCase().includes(needle))
      .sort((a, b) => (sort === 'created_at' ? b.created_at.localeCompare(a.created_at) : (b[sort] ?? 0) - (a[sort] ?? 0)))
  }, [reports, q, status, sort, each])

  const selected = reports?.find((r) => r.report_id === focus)
  if (!reports) return <div className="loading">Chargement…</div>

  return (
    <div className={selected ? 'page with-panel' : 'page'}>
      <div className="page-main">
        <header className="page-head">
          <div>
            <h1>Signalements</h1>
            <p className="muted">{rows.length} {each ? 'signalements' : 'nids-de-poule'} affichés</p>
          </div>
          <button className="btn ghost" onClick={() => exportCsv(rows)}><Icon name="download" size={15} /> Exporter CSV</button>
        </header>

        <div className="toolbar">
          <label className="search">
            <Icon name="search" size={16} />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Référence, rue, quartier, service…" />
          </label>
          <select value={status} onChange={(e) => setStatus(e.target.value as Status | '')}>
            <option value="">Tous les statuts</option>
            {(Object.keys(STATUS) as Status[]).map((s) => <option key={s} value={s}>{STATUS[s].label}</option>)}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
            {(Object.keys(SORTS) as Sort[]).map((s) => <option key={s} value={s}>Trier : {SORTS[s]}</option>)}
          </select>
          <label className="toggle">
            <input type="checkbox" checked={each} onChange={(e) => setEach(e.target.checked)} /> Chaque signalement
          </label>
        </div>

        <div className="card flush">
          <table className="table">
            <thead>
              <tr><th>Réf.</th><th>Adresse</th><th>Sévérité</th><th>Statut</th><th>Citoyens</th><th>Service</th><th>Signalé le</th><th>Échéance</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.report_id} onClick={() => go('reports', r.report_id)}
                  className={r.report_id === focus ? 'clickable selected' : 'clickable'}>
                  <td className="mono">{r.ref}</td>
                  <td className="ellipsis">{r.address ?? '—'}</td>
                  <td><Severity score={r.score} /></td>
                  <td><StatusBadge status={r.status} /></td>
                  <td>{r.cluster_size}</td>
                  <td>{r.target_office === 'Municipality' ? 'Municipalité' : r.target_office ?? '—'}</td>
                  <td>{date(r.created_at)}</td>
                  <td><Deadline r={r} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <p className="empty-row muted">Aucun signalement ne correspond.</p>}
        </div>
      </div>
      {selected && (
        <ReportPanel r={selected} onClose={() => go('reports')} onChanged={onChanged} onShowOnMap={() => go('map', selected.report_id)} />
      )}
    </div>
  )
}

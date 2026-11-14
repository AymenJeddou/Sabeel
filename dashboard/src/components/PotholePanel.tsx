import { useState } from 'react'
import { api, date, dateTime, type PotholeDetail, usePoll } from '../api'
import { EVENT, PRIORITY_PARTS, ROAD_CLASS, SOURCE, STATUS } from '../i18n'
import { Deadline, ErrorNote, Icon, Loading, PhotoWithBoxes, Severity, SheetBadge, StatusBadge } from '../ui'

/** LLM sheets may use **bold**: shown as bold, never as raw asterisks. */
const boldText = (text: string) =>
  text.replace(/^\s*[*-]\s+/gm, '• ').split(/\*\*(.+?)\*\*/g).map((part, i) => (i % 2 ? <b key={i}>{part}</b> : part))

/** The full case file of one pothole and every action an officer can take on it. */
export default function PotholePanel({ id, onClose, onChanged, onShowOnMap }: {
  id: string
  onClose: () => void
  onChanged: () => void
  onShowOnMap?: () => void
}) {
  const { data: p, error, refresh } = usePoll(() => api.pothole(id), 20000, [id])
  if (error && !p) return <aside className="panel"><div className="panel-body"><ErrorNote error={error} /></div></aside>
  if (!p) return <aside className="panel"><Loading /></aside>
  const changed = () => (refresh(), onChanged())
  return <Panel key={p.pothole_id + p.updated_at} p={p} onClose={onClose} onChanged={changed} onShowOnMap={onShowOnMap} />
}

function Panel({ p, onClose, onChanged, onShowOnMap }: { p: PotholeDetail; onClose: () => void; onChanged: () => void; onShowOnMap?: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [photo, setPhoto] = useState(0)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(p.sheet_text ?? '')
  const [fixing, setFixing] = useState(false)
  const [proof, setProof] = useState<File | null>(null)
  const [note, setNote] = useState('')

  const run = async (fn: () => Promise<unknown>, confirmText?: string) => {
    if (confirmText && !confirm(confirmText)) return
    setBusy(true)
    setError(null)
    try {
      await fn()
      onChanged()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const photos = p.reports.filter((r) => r.photo_url)
  const shown = photos[Math.min(photo, photos.length - 1)]
  const open = ['new', 'confirmed', 'sheet_sent', 'reopened'].includes(p.status)
  const canFix = (p.status === 'sheet_sent' || p.status === 'reopened' || (p.status === 'confirmed' && (p.severity ?? 0) < 3))

  return (
    <aside className="panel">
      <header className="panel-head">
        <div>
          <div className="ref">{p.ref}</div>
          <h3>{p.address_label ?? 'Adresse en cours d’identification'}</h3>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Fermer"><Icon name="x" /></button>
      </header>

      {shown?.photo_url && <PhotoWithBoxes src={shown.photo_url} boxes={shown.boxes} alt={`Photo du signalement ${p.ref}`} />}
      {photos.length > 1 && (
        <div className="photo-dots">
          {photos.map((r, i) => (
            <button key={r.report_id} className={i === photo ? 'active' : ''} onClick={() => setPhoto(i)} aria-label={`Photo ${i + 1}`} />
          ))}
        </div>
      )}

      <div className="panel-body">
        <div className="panel-row"><StatusBadge status={p.status} /><Severity score={p.severity} /></div>
        {p.needs_review && <p className="notice warn"><Icon name="eye" size={14} /> À vérifier : {p.fix_check?.detected ? 'l’IA voit encore un nid-de-poule sur la photo de réparation.' : 'le modèle n’a pas confirmé ou des citoyens contestent.'}</p>}
        {p.escalated_at && <p className="notice critical"><Icon name="alert" size={14} /> Escaladé le {date(p.escalated_at)} faute d’intervention dans les délais.</p>}

        <dl className="facts">
          <dt>Priorité</dt>
          <dd>
            <b>{Math.round(p.priority_score)}</b>
            <span className="parts">
              {Object.entries(p.priority_components).filter(([, v]) => v > 0).map(([k, v]) => (
                <span key={k} className="part">{PRIORITY_PARTS[k] ?? k} +{Math.round(v * 10) / 10}</span>
              ))}
            </span>
          </dd>
          <dt>Échéance</dt><dd><Deadline p={p} /></dd>
          <dt>Citoyens</dt><dd>{p.device_count} appareil{p.device_count > 1 ? 's' : ''} · {p.report_count} photo{p.report_count > 1 ? 's' : ''} · {p.confirm_count} « je le vois aussi »</dd>
          <dt>Route</dt><dd>{[p.road_ref, ROAD_CLASS[p.road_class ?? ''] ?? p.road_class].filter(Boolean).join(' · ') || '—'}</dd>
          <dt>Bureau</dt><dd>{p.target_office ?? 'Non attribué'}</dd>
          <dt>Confiance IA</dt><dd>{p.max_confidence != null ? `${Math.round(p.max_confidence * 100)} %` : '—'}</dd>
          {p.rain_mm_48h != null && <><dt>Pluie 48 h</dt><dd><Icon name="cloud" size={13} /> {p.rain_mm_48h} mm</dd></>}
          <dt>GPS</dt>
          <dd className="mono">
            {p.lat.toFixed(5)}, {p.lon.toFixed(5)}{' '}
            <a href={`https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}`} target="_blank" rel="noreferrer" title="Itinéraire">
              <Icon name="external" size={13} />
            </a>
          </dd>
          {p.repair_method && <><dt>Méthode</dt><dd className="method">{p.repair_method}</dd></>}
        </dl>

        {p.sheet_status && (
          <section className="sheet">
            <div className="row-between">
              <b><Icon name="file" size={14} /> Fiche de travaux</b>
              <SheetBadge status={p.sheet_status} />
            </div>
            {p.sheet_status === 'queued' && <p className="muted small">Rédaction en cours (tâche en arrière-plan){p.sheet_job?.attempts ? ` · tentative ${p.sheet_job.attempts}` : ''}.</p>}
            {p.sheet_status === 'failed' && <p className="error small">Échec : {p.sheet_job?.last_error ?? 'service indisponible'}.</p>}
            {editing ? (
              <textarea className="sheet-edit" rows={12} value={draft} onChange={(e) => setDraft(e.target.value)} />
            ) : (
              p.sheet_text && <pre>{boldText(p.sheet_text)}</pre>
            )}
            {!!p.sheet_citations.length && (
              <ul className="citations">
                {p.sheet_citations.map((c) => <li key={c.rule_id}><b>{c.rule_id}</b> · {c.source}</li>)}
              </ul>
            )}
            {p.sheet_approved_at && (
              <p className="muted small">
                Approuvée le {dateTime(p.sheet_approved_at)} par {p.sheet_approved_by} · empreinte <span className="mono">{p.sheet_hash?.slice(0, 16)}</span>
                {p.sheet_edited && ' · modifiée avant approbation'}
              </p>
            )}
            <div className="sheet-actions">
              {p.sheet_status === 'generated' && !editing && <button className="btn ghost" onClick={() => setEditing(true)}><Icon name="edit" size={15} /> Modifier</button>}
              {editing && <>
                <button className="btn ghost" onClick={() => (setEditing(false), setDraft(p.sheet_text ?? ''))}>Annuler</button>
                <button className="btn primary" disabled={busy || draft.trim().length < 10} onClick={() => run(async () => { await api.editSheet(p.pothole_id, draft); setEditing(false) })}>Enregistrer</button>
              </>}
              {p.sheet_status === 'generated' && !editing && (
                <button className="btn primary" disabled={busy} onClick={() => run(() => api.approveSheet(p.pothole_id), `Approuver et transmettre la fiche ${p.ref} ?`)}>
                  <Icon name="check" size={15} /> Approuver et transmettre
                </button>
              )}
              {(p.sheet_status === 'failed' || (p.sheet_status === 'generated' && !editing)) && (
                <button className="btn ghost" disabled={busy} onClick={() => run(() => api.retrySheet(p.pothole_id))}><Icon name="refresh" size={15} /> {p.sheet_status === 'failed' ? 'Réessayer' : 'Régénérer'}</button>
              )}
              {p.sheet_text && <button className="btn ghost" onClick={() => api.download(`/potholes/${p.pothole_id}/sheet.pdf`, `fiche-${p.ref}.pdf`).catch((e) => setError(e.message))}><Icon name="download" size={15} /> PDF</button>}
            </div>
          </section>
        )}

        {p.status === 'fixed' || p.fixed_proof_url ? (
          <section className="sheet">
            <div className="row-between">
              <b><Icon name="wrench" size={14} /> Réparation</b>
              {p.fix_check && (p.fix_check.detected
                ? <span className="badge tone-critical"><Icon name="alert" size={12} /> IA : encore visible</span>
                : <span className="badge tone-good"><Icon name="shield" size={12} /> Vérifiée par l’IA</span>)}
            </div>
            {p.fixed_proof_url && <PhotoWithBoxes src={p.fixed_proof_url} boxes={p.fix_check?.boxes ?? []} alt="Photo de la réparation" />}
            <p className="small">{p.fixed_note} {p.fixed_at && <span className="muted">· {dateTime(p.fixed_at)}</span>}</p>
            <p className="muted small">{p.fixed_ok_count} citoyen(s) confirment · {p.not_fixed_count} disent « toujours là »</p>
          </section>
        ) : null}

        {fixing && (
          <form className="sheet" onSubmit={(e) => (e.preventDefault(), proof && run(async () => { await api.fix(p.pothole_id, proof, note); setFixing(false) }))}>
            <b><Icon name="camera" size={14} /> Preuve de réparation</b>
            <label className="field">Photo de l’endroit réparé (obligatoire)
              <input type="file" accept="image/jpeg,image/png" capture="environment" required onChange={(e) => setProof(e.target.files?.[0] ?? null)} />
            </label>
            <label className="field">Note
              <textarea rows={2} required minLength={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ex. : découpe, enrobé à chaud, compactage" />
            </label>
            <p className="muted small">Le modèle vérifie la photo : s’il voit encore un nid-de-poule, la réparation sera signalée à vérifier.</p>
            <div className="sheet-actions">
              <button type="button" className="btn ghost" onClick={() => setFixing(false)}>Annuler</button>
              <button className="btn primary" disabled={busy || !proof || note.trim().length < 3}><Icon name="check" size={15} /> Valider la réparation</button>
            </div>
          </form>
        )}

        <section>
          <b className="small">Historique</b>
          <ol className="timeline">
            {[...p.events].reverse().map((e, i) => (
              <li key={i}>
                <span>{EVENT[e.kind] ?? e.kind}{e.to_status && e.kind === 'status' ? ` → ${STATUS[e.to_status as keyof typeof STATUS]?.label ?? e.to_status}` : ''}</span>
                <span className="muted small">{dateTime(e.created_at)} · {e.actor.replace('office:', '').replace(/^device:.*/, 'citoyen')}{e.note ? ` · ${e.note}` : ''}</span>
              </li>
            ))}
          </ol>
        </section>

        <section>
          <b className="small">Signalements ({p.reports.length})</b>
          <ul className="reports-mini">
            {p.reports.map((r) => (
              <li key={r.report_id}>
                <Icon name={r.source === 'driving_mode' ? 'car' : 'hand'} size={13} />
                <span>{SOURCE[r.source]} · {dateTime(r.captured_at)}</span>
                <span className="muted small">{r.detected ? `IA ${r.score}/5 · ${Math.round((r.confidence ?? 0) * 100)} %` : 'IA : rien détecté'}{r.gps_accuracy_m != null ? ` · ±${Math.round(r.gps_accuracy_m)} m` : ''}</span>
              </li>
            ))}
          </ul>
        </section>
        <ErrorNote error={error} />
      </div>

      <footer className="panel-actions">
        {onShowOnMap && <button className="btn ghost" onClick={onShowOnMap}><Icon name="map" size={15} /> Carte</button>}
        {open && (
          <button className="btn ghost danger" disabled={busy} onClick={() => run(() => api.setStatus(p.pothole_id, 'rejected', 'faux positif'), `Rejeter ${p.ref} comme faux positif ? La photo servira à réentraîner le modèle.`)}>
            <Icon name="ban" size={15} /> Pas un nid-de-poule
          </button>
        )}
        {p.status === 'new' && (
          <button className="btn primary" disabled={busy} onClick={() => run(() => api.setStatus(p.pothole_id, 'confirmed', 'confirmé manuellement'))}>
            <Icon name="users" size={15} /> Confirmer
          </button>
        )}
        {canFix && !fixing && <button className="btn primary" onClick={() => setFixing(true)}><Icon name="wrench" size={15} /> Marquer réparé</button>}
      </footer>
    </aside>
  )
}

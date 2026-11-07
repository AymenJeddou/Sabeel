import { useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import { ErrorNote, Icon, Mark } from '../ui'
import { flushPending, savePending } from './pending'
import { deviceId, downscale, type Fix, rememberReport, reportFields } from './report'

type Phase = 'locating' | 'denied' | 'ready' | 'sending' | 'not_detected' | 'done' | 'queued'

/** Report a pothole from any phone browser, no install (issue #34). */
export default function ReportPage() {
  const [fix, setFix] = useState<Fix | null>(null)
  const [phase, setPhase] = useState<Phase>('locating')
  const [photo, setPhoto] = useState<Blob | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [result, setResult] = useState<{ id: string; ref: string | null } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [flushed, setFlushed] = useState(0)
  const pending = useRef<{ id: string; fields: Record<string, string>; at: Date } | null>(null)

  // Watch the position until it is better than 20 m or 8 s have passed.
  useEffect(() => {
    if (!('geolocation' in navigator)) return setPhase('denied')
    const started = Date.now()
    const watch = navigator.geolocation.watchPosition(
      (p) => {
        const f = { lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy, speed: p.coords.speed, heading: p.coords.heading }
        setFix(f)
        if (f.accuracy <= 20 || Date.now() - started > 8000) setPhase((ph) => (ph === 'locating' ? 'ready' : ph))
      },
      (e) => setPhase(e.code === e.PERMISSION_DENIED ? 'denied' : 'ready'),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
    )
    const t = setTimeout(() => setPhase((ph) => (ph === 'locating' ? 'ready' : ph)), 8000)
    return () => (navigator.geolocation.clearWatch(watch), clearTimeout(t))
  }, [])

  // Retry reports saved while offline: now, and whenever the connection returns.
  useEffect(() => {
    const flush = () => flushPending(api.submitReport).then((n) => n && setFlushed((x) => x + n))
    flush()
    addEventListener('online', flush)
    return () => removeEventListener('online', flush)
  }, [])

  const pick = async (file: File | undefined) => {
    if (!file) return
    setError(null)
    const small = await downscale(file).catch(() => file)
    setPhoto(small)
    setPreview(URL.createObjectURL(small))
  }

  const send = async (force = false) => {
    if (!photo || !fix) return
    setPhase('sending')
    setError(null)
    // Same device_report_id for "send anyway" and for every retry.
    pending.current ??= { id: crypto.randomUUID(), fields: {}, at: new Date() }
    const fields = reportFields(fix, pending.current.at, pending.current.id, deviceId(), force)
    const form = new FormData()
    for (const [k, v] of Object.entries(fields)) form.set(k, v)
    form.set('photo', photo, 'photo.jpg')
    try {
      const r = await api.submitReport(form)
      rememberReport(r.device_report_id)
      if (!r.detected && !r.pothole_id) return setPhase('not_detected')
      setResult({ id: r.device_report_id, ref: r.ref })
      setPhase('done')
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0
      if (status === 429) {
        setError('Trop de signalements en peu de temps. Réessayez dans quelques minutes.')
        return setPhase('ready')
      }
      if (status && status < 500) {
        setError(e instanceof Error ? e.message : String(e))
        return setPhase('ready')
      }
      await savePending({ device_report_id: fields.device_report_id, fields, photo, saved_at: new Date().toISOString() }).catch(() => null)
      rememberReport(fields.device_report_id)
      setResult({ id: fields.device_report_id, ref: null })
      setPhase('queued')
    }
  }

  const reset = () => {
    pending.current = null
    setPhoto(null)
    setPreview(null)
    setResult(null)
    setPhase(fix ? 'ready' : 'locating')
  }

  return (
    <div className="public report-page">
      <header className="public-head">
        <a href="#/" className="brand-inline"><Mark size={30} /><b>Sabeel</b></a>
        <span className="muted small">Signaler un nid-de-poule</span>
      </header>

      <main className="report-card">
        {flushed > 0 && <p className="notice good"><Icon name="check" size={14} /> {flushed} signalement(s) en attente envoyé(s).</p>}

        {phase === 'denied' && (
          <div className="notice warn">
            <b>La localisation est nécessaire.</b>
            <p>Sabeel a besoin de la position exacte du nid-de-poule pour l’envoyer au bon service (municipalité ou direction régionale).
              Elle sert uniquement à placer le nid-de-poule sur la carte, jamais à suivre vos trajets.</p>
            <p className="small">Autorisez la localisation pour ce site dans les réglages du navigateur, puis rechargez la page.</p>
          </div>
        )}

        {(phase === 'locating' || phase === 'ready' || phase === 'sending') && (
          <>
            <div className={`gps ${fix && fix.accuracy <= 20 ? 'good' : ''}`}>
              <Icon name="pin" size={16} />
              {fix ? <>Position à ±{Math.round(fix.accuracy)} m {fix.accuracy > 20 && phase === 'locating' && '· amélioration…'}</> : 'Recherche de la position…'}
            </div>
            <label className={`shutter ${preview ? 'has-photo' : ''}`}>
              {preview ? <img src={preview} alt="Aperçu de la photo" /> : (
                <span><Icon name="camera" size={40} /><b>Prendre une photo</b><small>Approchez-vous et cadrez le trou entier</small></span>
              )}
              <input type="file" accept="image/*" capture="environment" onChange={(e) => pick(e.target.files?.[0])} />
            </label>
            <ErrorNote error={error} />
            <button className="btn primary wide big" disabled={!photo || !fix || phase === 'sending'} onClick={() => send()}>
              <Icon name="send" size={18} /> {phase === 'sending' ? 'Envoi…' : 'Envoyer le signalement'}
            </button>
            <p className="muted small center">Aucun compte. La photo est floutée (visages, plaques) et ses métadonnées supprimées avant stockage.</p>
          </>
        )}

        {phase === 'not_detected' && (
          <div className="result">
            <Icon name="eye" size={36} />
            <h2>Aucun nid-de-poule détecté</h2>
            <p className="muted">Le modèle ne voit pas de nid-de-poule sur cette photo. Reprenez-la de plus près, ou envoyez-la quand même : un agent la vérifiera.</p>
            <div className="toolbar center">
              <button className="btn ghost" onClick={reset}><Icon name="camera" size={15} /> Reprendre</button>
              <button className="btn primary" onClick={() => send(true)}><Icon name="send" size={15} /> Envoyer quand même</button>
            </div>
          </div>
        )}

        {(phase === 'done' || phase === 'queued') && result && (
          <div className="result">
            <Icon name={phase === 'done' ? 'check' : 'clock'} size={40} />
            <h2>{phase === 'done' ? 'Merci, signalement reçu !' : 'Enregistré, envoi dès le retour du réseau'}</h2>
            {result.ref && <p className="ref-big mono">{result.ref}</p>}
            <p className="muted">Suivez son traitement : reçu, confirmé, transmis, réparé.</p>
            <div className="toolbar center">
              <a className="btn primary" href={`#/track/${result.id}`}><Icon name="eye" size={15} /> Suivre</a>
              <button className="btn ghost" onClick={reset}><Icon name="camera" size={15} /> Nouveau signalement</button>
            </div>
            <p className="muted small">Astuce : ajoutez Sabeel à l’écran d’accueil pour signaler en un geste.</p>
          </div>
        )}
      </main>
    </div>
  )
}

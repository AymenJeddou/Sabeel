import { useEffect, useRef, useState } from 'react'
import { ago, api, citizen, go, initials, usePoll, type Conversation, type Report } from '../api'
import { Icon, Severity, StatusBadge } from '../ui'

const QUICK_REPLIES = [
  'Merci pour votre signalement, il est bien pris en compte.',
  "Une équipe d'intervention est planifiée cette semaine.",
  'Ce tronçon relève de la DGPC : le dossier lui a été transmis.',
  'Le nid-de-poule a été réparé. Merci pour votre vigilance !',
]

const time = (iso: string) => new Date(iso).toLocaleString('fr-TN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })

function Thread({ deviceId, reports, onSent }: { deviceId: string; reports: Report[]; onSent: () => void }) {
  const { data: messages, refresh } = usePoll(() => api.messages(deviceId), 4000, [deviceId])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }) }, [messages?.length])

  const send = async (text = draft) => {
    if (!text.trim()) return
    setSending(true)
    try {
      await api.reply(deviceId, text.trim())
      setDraft('')
      refresh()
      onSent()
    } finally {
      setSending(false)
    }
  }
  const theirs = reports.filter((r) => r.device_id === deviceId)

  return (
    <>
      <section className="thread">
        <header className="thread-head">
          <span className="avatar">{initials(deviceId).slice(-2)}</span>
          <div>
            <b>{citizen(deviceId)}</b>
            <div className="muted small">{theirs.length} signalement{theirs.length > 1 ? 's' : ''} · application mobile Sabeel</div>
          </div>
        </header>
        <div className="bubbles">
          {messages?.map((m) => (
            <div key={m.message_id} className={`bubble ${m.sender}`} dir="auto">
              {m.body}
              <time>{time(m.created_at)}</time>
            </div>
          ))}
          <div ref={end} />
        </div>
        <div className="quick">
          {QUICK_REPLIES.map((t) => (
            <button key={t} className="chip" onClick={() => setDraft(t)}>{t}</button>
          ))}
        </div>
        <form className="composer" onSubmit={(e) => (e.preventDefault(), send())}>
          <textarea
            value={draft}
            dir="auto"
            rows={2}
            placeholder="Répondre au citoyen…"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          />
          <button className="btn primary" disabled={sending || !draft.trim()}><Icon name="send" size={15} /> Envoyer</button>
        </form>
      </section>

      <aside className="panel context">
        <header className="panel-head"><div><div className="ref">Contexte</div><h3>Ses signalements</h3></div></header>
        <ul className="pothole-list">
          {theirs.map((r) => (
            <li key={r.report_id} onClick={() => go('map', r.report_id)}>
              {r.photo_url && <img src={r.photo_url} alt="" className="thumb" />}
              <div className="grow">
                <div className="row-between"><b className="mono">{r.ref}</b><span className="muted small">{ago(r.created_at)}</span></div>
                <div className="ellipsis">{r.address ?? '—'}</div>
                <div className="row-between"><StatusBadge status={r.status} /><Severity score={r.score} /></div>
              </div>
            </li>
          ))}
          {!theirs.length && <li className="muted">Aucun signalement lié à cet appareil.</li>}
        </ul>
      </aside>
    </>
  )
}

export default function Messages({ convos, reports, focus, onSent }: {
  convos: Conversation[] | null
  reports: Report[] | null
  focus?: string
  onSent: () => void
}) {
  if (!convos || !reports) return <div className="loading">Chargement…</div>
  const active = focus ?? convos[0]?.device_id

  return (
    <div className="messages-page">
      <aside className="inbox">
        <header className="inbox-head">
          <h1>Messages</h1>
          <span className="muted small">{convos.filter((c) => c.last_sender === 'citizen').length} en attente de réponse</span>
        </header>
        <ul>
          {convos.map((c) => (
            <li key={c.device_id} className={c.device_id === active ? 'active' : ''} onClick={() => go('messages', c.device_id)}>
              <span className="avatar">{initials(c.device_id).slice(-2)}</span>
              <div className="grow">
                <div className="row-between">
                  <b>{citizen(c.device_id)}</b>
                  <span className="muted small">{ago(c.last_at)}</span>
                </div>
                <div className="ellipsis muted" dir="auto">{c.last_sender === 'authority' && 'Vous : '}{c.last_body}</div>
              </div>
              {c.last_sender === 'citizen' && <span className="unread" title="En attente de réponse" />}
            </li>
          ))}
        </ul>
      </aside>
      {active ? <Thread key={active} deviceId={active} reports={reports} onSent={onSent} /> : <div className="empty">Aucune conversation.</div>}
    </div>
  )
}

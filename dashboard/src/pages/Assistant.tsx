import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { latLngBounds } from 'leaflet'
import { api, go, severityColor, type Pothole } from '../api'
import { Icon, Severity, StatusBadge } from '../ui'

interface Turn {
  role: 'user' | 'assistant'
  content: string
  refs?: Pothole[]
  source?: 'llm' | 'fallback'
}

const PROMPTS = [
  'Quels sont les 5 nids-de-poule les plus urgents et où sont-ils exactement ?',
  'Lesquels ont dépassé leur échéance de réparation ?',
  'Comment réparer un nid-de-poule de sévérité 4 ?',
  'Quel quartier est le plus touché et que recommandes-tu ?',
  'Fais-moi un bilan de la semaine pour le conseil municipal.',
  'What is the median repair time and how can we improve it?',
]

/** TN-XXXXXX in the answer become links to the map; **bold** and "- " bullets are honoured. */
function Rich({ text, refs }: { text: string; refs: Pothole[] }) {
  const byRef = new Map(refs.map((r) => [r.ref, r]))
  const inline = (s: string): ReactNode[] =>
    s.split(/(\*\*[^*]+\*\*|TN-[0-9A-F]{6})/g).map((part, i) => {
      if (part.startsWith('**')) return <b key={i}>{part.slice(2, -2)}</b>
      const r = byRef.get(part)
      return r ? <a key={i} className="ref-link" onClick={() => go('map', r.pothole_id)}>{part}</a> : <Fragment key={i}>{part}</Fragment>
    })
  const blocks: ReactNode[] = []
  let items: ReactNode[] = []
  const flush = () => items.length && (blocks.push(<ul key={blocks.length}>{items}</ul>), (items = []))
  for (const line of text.split('\n')) {
    // Markdown headings ("### 3. Next") become a bold line, never raw hashes.
    const heading = line.match(/^\s*#{1,6}\s+(.*)/)
    if (heading) {
      flush()
      blocks.push(<p key={blocks.length}><b>{inline(heading[1].replace(/\*\*/g, ''))}</b></p>)
      continue
    }
    const bullet = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)/)
    if (bullet && !bullet[1].trim()) continue
    if (bullet) items.push(<li key={items.length}>{inline(bullet[1])}</li>)
    else {
      flush()
      if (line.trim()) blocks.push(<p key={blocks.length}>{inline(line)}</p>)
    }
  }
  flush()
  return <div className="rich" dir="auto">{blocks}</div>
}

function Fit({ refs }: { refs: Pothole[] }) {
  const map = useMap()
  useEffect(() => {
    if (refs.length) map.fitBounds(latLngBounds(refs.map((r) => [r.lat, r.lon])), { padding: [40, 40], maxZoom: 16 })
  }, [refs, map])
  return null
}

export default function Assistant() {
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [turns.length, thinking])

  const cited = [...turns].reverse().find((t) => t.refs?.length)?.refs ?? []

  const ask = async (question: string) => {
    if (!question.trim() || thinking) return
    const history = turns.slice(-6).map(({ role, content }) => ({ role, content })) // the API reads the last 6
    setTurns((t) => [...t, { role: 'user', content: question.trim() }])
    setDraft('')
    setThinking(true)
    try {
      const reply = await api.ask(question.trim(), history)
      setTurns((t) => [...t, { role: 'assistant', content: reply.answer, refs: reply.refs, source: reply.source }])
    } catch (e) {
      setTurns((t) => [...t, { role: 'assistant', content: `Erreur : ${(e as Error).message}` }])
    } finally {
      setThinking(false)
    }
  }

  return (
    <div className="assistant-page">
      <section className="assistant">
        <div className="bubbles">
          {!turns.length && (
            <div className="hello">
              <img src="/assist.png" alt="" className="bot-lg" />
              <h1>Sabeel Assist</h1>
              <p className="muted">
                Posez vos questions sur les nids-de-poule de votre bureau : localisation exacte, priorités, retards,
                statistiques, méthodes de réparation. Réponses fondées uniquement sur les données Sabeel.
              </p>
              <div className="prompts">
                {PROMPTS.map((p) => <button key={p} className="prompt" onClick={() => ask(p)}>{p}</button>)}
              </div>
            </div>
          )}
          {turns.map((t, i) =>
            t.role === 'user' ? (
              <div key={i} className="bubble authority" dir="auto">{t.content}</div>
            ) : (
              <div key={i} className="bot-turn">
                <img src="/assist.png" alt="" className="bot" />
                <div className="bot-body">
                  <Rich text={t.content} refs={t.refs ?? []} />
                  {!!t.refs?.length && (
                    <div className="ref-cards">
                      {t.refs.map((r) => (
                        <button key={r.pothole_id} className="ref-card" onClick={() => go('map', r.pothole_id)}>
                          <span className="row-between"><b className="mono">{r.ref}</b><Severity score={r.severity} /></span>
                          <span className="ellipsis">{r.address_label}</span>
                          <span className="row-between"><StatusBadge status={r.status} /><span className="link"><Icon name="map" size={13} /> Voir</span></span>
                        </button>
                      ))}
                    </div>
                  )}
                  {t.source === 'fallback' && <p className="muted small">Réponse générée sans le modèle de langage (indisponible).</p>}
                </div>
              </div>
            ),
          )}
          {thinking && (
            <div className="bot-turn">
              <img src="/assist.png" alt="" className="bot" />
              <div className="typing"><i /><i /><i /></div>
            </div>
          )}
          <div ref={end} />
        </div>
        <form className="composer" onSubmit={(e) => (e.preventDefault(), ask(draft))}>
          <textarea
            value={draft}
            dir="auto"
            rows={2}
            placeholder="Ex. : Où sont les nids-de-poule urgents à La Marsa ?"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), ask(draft))}
          />
          <button className="btn primary" disabled={thinking || !draft.trim()}><Icon name="send" size={15} /> Envoyer</button>
        </form>
      </section>

      <aside className="panel assistant-map">
        <header className="panel-head">
          <div>
            <div className="ref">Localisations citées</div>
            <h3>{cited.length ? `${cited.length} nid${cited.length > 1 ? 's' : ''}-de-poule` : 'Aucune pour le moment'}</h3>
          </div>
        </header>
        <MapContainer center={[36.822, 10.2]} zoom={11} className="map" zoomControl={false}>
          <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
          {cited.map((r) => (
            <CircleMarker key={r.pothole_id} center={[r.lat, r.lon]} radius={10}
              pathOptions={{ color: '#fff', weight: 2, fillColor: severityColor(r.severity), fillOpacity: 0.95 }}
              eventHandlers={{ click: () => go('map', r.pothole_id) }}>
              <Tooltip permanent direction="top" offset={[0, -10]}>{r.ref}</Tooltip>
            </CircleMarker>
          ))}
          <Fit refs={cited} />
        </MapContainer>
      </aside>
    </div>
  )
}

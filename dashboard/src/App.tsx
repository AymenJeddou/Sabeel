import { useEffect, useState } from 'react'
import { api, usePoll } from './api'
import { Icon, Mark, type IconName } from './ui'
import Overview from './pages/Overview'
import MapPage from './pages/MapPage'
import Reports from './pages/Reports'
import Messages from './pages/Messages'
import Assistant from './pages/Assistant'

const PAGES: { id: string; label: string; icon: IconName }[] = [
  { id: 'overview', label: "Vue d'ensemble", icon: 'grid' },
  { id: 'map', label: 'Carte', icon: 'map' },
  { id: 'reports', label: 'Signalements', icon: 'list' },
  { id: 'messages', label: 'Messages', icon: 'chat' },
  { id: 'assistant', label: 'Sabeel Assist', icon: 'spark' },
]

/** "#/map/<report_id>" -> ["map", "<report_id>"]. The hash is the whole router. */
function useHash(): [string, string | undefined] {
  const read = () => location.hash.replace(/^#\/?/, '').split('/')
  const [parts, setParts] = useState(read)
  useEffect(() => {
    const on = () => setParts(read())
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])
  return [PAGES.some((p) => p.id === parts[0]) ? parts[0] : 'overview', parts[1] || undefined]
}

export default function App() {
  const [page, id] = useHash()
  const reports = usePoll(api.reports)
  const stats = usePoll(api.stats)
  const convos = usePoll(api.conversations, 5000)
  const refresh = () => (reports.refresh(), stats.refresh())

  const waiting = convos.data?.filter((c) => c.last_sender === 'citizen').length ?? 0
  const badges: Record<string, number> = { reports: stats.data?.overdue ?? 0, messages: waiting }
  const offline = reports.error && !reports.data

  return (
    <div className="shell">
      <nav className="sidebar">
        <a className="brand" href="#/overview">
          <Mark size={34} color="#fff" />
          <span>
            <b>Sabeel</b>
            <small>Espace Autorités</small>
          </span>
        </a>
        {PAGES.map((p) => (
          <a key={p.id} href={`#/${p.id}`} className={page === p.id ? 'nav active' : 'nav'}>
            <Icon name={p.icon} />
            {p.label}
            {badges[p.id] > 0 && <span className="nav-badge">{badges[p.id]}</span>}
          </a>
        ))}
        <div className="sidebar-foot">
          <span className={offline ? 'live off' : 'live'} />
          {offline ? 'API injoignable' : 'Données en direct'}
          <small>Grand Tunis · Municipalité &amp; DGPC</small>
        </div>
      </nav>

      <main className="main">
        {offline ? (
          <div className="empty">
            <Icon name="alert" size={28} />
            <p>Impossible de joindre l'API Sabeel ({reports.error}).<br />Lancez le backend sur le port 8002.</p>
          </div>
        ) : page === 'overview' ? (
          <Overview reports={reports.data} stats={stats.data} />
        ) : page === 'map' ? (
          <MapPage reports={reports.data} focus={id} onChanged={refresh} />
        ) : page === 'reports' ? (
          <Reports reports={reports.data} focus={id} onChanged={refresh} />
        ) : page === 'messages' ? (
          <Messages convos={convos.data} reports={reports.data} focus={id} onSent={convos.refresh} />
        ) : (
          <Assistant />
        )}
      </main>
    </div>
  )
}

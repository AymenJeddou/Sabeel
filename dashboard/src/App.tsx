import { lazy, Suspense, useEffect, useState } from 'react'
import { api, getToken, setToken, usePoll, type Office } from './api'
import { Icon, Loading, Mark, type IconName } from './ui'
import Login from './pages/Login'

// Officer pages
const Overview = lazy(() => import('./pages/Overview'))
const Queue = lazy(() => import('./pages/Queue'))
const MapPage = lazy(() => import('./pages/MapPage'))
const Analytics = lazy(() => import('./pages/Analytics'))
const RoutePlanner = lazy(() => import('./pages/RoutePlanner'))
const Messages = lazy(() => import('./pages/Messages'))
const Assistant = lazy(() => import('./pages/Assistant'))
// Public pages (no login)
const PublicHome = lazy(() => import('./public/PublicHome'))
const ReportPage = lazy(() => import('./public/ReportPage'))
const TrackPage = lazy(() => import('./public/TrackPage'))
const VerifyPage = lazy(() => import('./public/VerifyPage'))

const PAGES: { id: string; label: string; icon: IconName }[] = [
  { id: 'overview', label: "Vue d'ensemble", icon: 'grid' },
  { id: 'queue', label: 'File de travail', icon: 'list' },
  { id: 'map', label: 'Carte', icon: 'map' },
  { id: 'route', label: 'Tournée du jour', icon: 'route' },
  { id: 'analytics', label: 'Analyses', icon: 'chart' },
  { id: 'messages', label: 'Messages', icon: 'chat' },
  { id: 'assistant', label: 'Sabeel Assist', icon: 'spark' },
]
const PUBLIC = ['', 'public', 'report', 'track', 'p', 'verify']

export interface Route { page: string; id?: string; query: URLSearchParams }

/** "#/map/<id>?x=1" -> {page: "map", id, query}. The hash is the whole router. */
function useHash(): Route {
  const read = (): Route => {
    const [path, q = ''] = location.hash.replace(/^#\/?/, '').split('?')
    const [page = '', id] = path.split('/')
    return { page, id: id || undefined, query: new URLSearchParams(q) }
  }
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const on = () => setRoute(read())
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])
  return route
}

export default function App() {
  const route = useHash()
  const [office, setOffice] = useState<Office | null>(null)
  const [checking, setChecking] = useState(!!getToken())

  useEffect(() => {
    const logout = () => (setToken(null), setOffice(null))
    addEventListener('sabeel:logout', logout)
    if (getToken()) api.me().then(setOffice, logout).finally(() => setChecking(false))
    return () => removeEventListener('sabeel:logout', logout)
  }, [])

  if (PUBLIC.includes(route.page)) {
    return (
      <Suspense fallback={<Loading />}>
        {route.page === 'report' ? <ReportPage /> : route.page === 'track' ? <TrackPage id={route.id} />
          : route.page === 'verify' ? <VerifyPage id={route.id} h={route.query.get('h') ?? ''} /> : <PublicHome focus={route.page === 'p' ? route.id : undefined} />}
      </Suspense>
    )
  }
  if (checking) return <Loading />
  if (!office) return <Login onLogin={(o) => setOffice(o)} />
  return <OfficeShell office={office} route={route} onLogout={() => (setToken(null), setOffice(null))} />
}

function OfficeShell({ office, route, onLogout }: { office: Office; route: Route; onLogout: () => void }) {
  const page = PAGES.some((p) => p.id === route.page) ? route.page : 'overview'
  const summary = usePoll(() => api.summary(), 30000)
  const convos = usePoll(api.conversations, 10000)
  const [version, setVersion] = useState(0)
  const changed = () => (setVersion((v) => v + 1), summary.refresh())

  const waiting = convos.data?.filter((c) => c.last_sender === 'citizen').length ?? 0
  const badges: Record<string, number> = { queue: summary.data?.overdue ?? 0, messages: waiting }

  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Navigation">
        <a className="brand" href="#/overview">
          <Mark size={34} color="#fff" />
          <span>
            <b>Sabeel</b>
            <small>Espace Autorités</small>
          </span>
        </a>
        {PAGES.map((p) => (
          <a key={p.id} href={`#/${p.id}`} className={page === p.id ? 'nav active' : 'nav'} aria-current={page === p.id ? 'page' : undefined}>
            <Icon name={p.icon} />
            <span className="nav-label">{p.label}</span>
            {badges[p.id] > 0 && <span className="nav-badge">{badges[p.id]}</span>}
          </a>
        ))}
        <div className="sidebar-foot">
          <span className={summary.error ? 'live off' : 'live'} />
          {summary.error ? 'API injoignable' : 'Données en direct'}
          <small>{office.name}{office.parent ? ` · rattaché à ${office.parent}` : ''}</small>
          <a className="nav small" href="#/public" target="_blank" rel="noreferrer"><Icon name="external" size={14} /> Page publique</a>
          <button className="nav small logout" onClick={onLogout}><Icon name="logout" size={14} /> Déconnexion</button>
        </div>
      </nav>

      <main className="main">
        <Suspense fallback={<Loading />}>
          {page === 'overview' ? <Overview office={office} summary={summary.data} version={version} />
            : page === 'queue' ? <Queue focus={route.id} onChanged={changed} version={version} />
            : page === 'map' ? <MapPage focus={route.id} onChanged={changed} version={version} />
            : page === 'route' ? <RoutePlanner office={office} />
            : page === 'analytics' ? <Analytics office={office} />
            : page === 'messages' ? <Messages convos={convos.data} focus={route.id} onSent={convos.refresh} />
            : <Assistant />}
        </Suspense>
      </main>
    </div>
  )
}

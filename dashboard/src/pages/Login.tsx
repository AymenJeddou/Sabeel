import { useState } from 'react'
import { api, setToken, type Office } from '../api'
import { ErrorNote, Icon, Mark } from '../ui'

/** MVP officer login: the office pastes the token it was given
 * (`python -m backend.app.scripts.seed_offices`). Kept in this tab only. */
export default function Login({ onLogin }: { onLogin: (o: Office) => void }) {
  const [value, setValue] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (token: string) => {
    setBusy(true)
    setError(null)
    setToken(token.trim())
    try {
      onLogin(await api.me())
    } catch (e) {
      setToken(null)
      setError((e as Error).message === 'Invalid office token' ? 'Jeton invalide.' : (e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <form className="login-card" onSubmit={(e) => (e.preventDefault(), submit(value))}>
        <Mark size={52} />
        <h1>Sabeel · Espace Autorités</h1>
        <p className="muted">Municipalités, directions régionales de l’Équipement et Ministère.</p>
        <label className="field">
          Jeton d’accès du bureau
          <input type="password" autoComplete="current-password" value={value} onChange={(e) => setValue(e.target.value)}
            placeholder="Collez le jeton fourni à votre bureau" required />
        </label>
        <ErrorNote error={error} />
        <button className="btn primary wide" disabled={busy || !value.trim()}><Icon name="shield" size={15} /> Se connecter</button>
        {(import.meta.env.DEV || import.meta.env.VITE_DEMO_LOGINS === '1') && (
          <div className="demo-logins">
            <span className="muted small">Démo locale (seed) :</span>
            {['mun-tunis', 'dre-tunis', 'ministry'].map((code) => (
              <button type="button" key={code} className="chip" onClick={() => submit(`demo-${code}`)}>{code}</button>
            ))}
          </div>
        )}
        <a className="link small" href="#/">← Page publique</a>
      </form>
    </div>
  )
}

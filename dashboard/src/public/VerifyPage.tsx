import { api, date, usePoll } from '../api'
import { ErrorNote, Icon, Loading, Mark } from '../ui'

/** Opened from the QR code printed on a work-order PDF: checks the fingerprint. */
export default function VerifyPage({ id, h }: { id?: string; h: string }) {
  const { data, error } = usePoll(() => (id && h ? api.verify(id, h) : Promise.reject(new Error('Lien incomplet.'))), 0, [id, h])
  return (
    <div className="public report-page">
      <header className="public-head"><a href="#/" className="brand-inline"><Mark size={30} /><b>Sabeel</b></a></header>
      <main className="report-card center">
        {!data && !error && <Loading />}
        <ErrorNote error={error} />
        {data && (data.valid ? (
          <div className="result">
            <span className="seal good"><Icon name="shield" size={40} /></span>
            <h2>Fiche authentique</h2>
            <p>La fiche <b className="mono">{data.ref}</b> correspond à la version approuvée le {data.approved_on && date(data.approved_on)} par {data.office}.</p>
          </div>
        ) : (
          <div className="result">
            <span className="seal bad"><Icon name="alert" size={40} /></span>
            <h2>Empreinte non reconnue</h2>
            <p>Ce document ne correspond pas à une fiche approuvée dans Sabeel pour <b className="mono">{data.ref}</b>. Il a pu être modifié.</p>
          </div>
        ))}
        <p className="muted small">L’empreinte est un hachage SHA-256 du texte approuvé, des textes cités, de la date et du bureau.</p>
      </main>
    </div>
  )
}

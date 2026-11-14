# Sabeel web app (officer dashboard + public site)

One React + TypeScript + Vite app, two audiences:

| Route | Who | What |
|---|---|---|
| `#/` | Everyone | Public transparency page: counters, open / fixed map, monthly trend, governorates (< 5 suppressed), worst streets, "Report" button |
| `#/report` | Everyone | Report a pothole from a phone browser, no install (PWA, offline queue in IndexedDB) |
| `#/track/<device_report_id>` | The reporter | 4-step tracker (Reçu → Confirmé → Transmis → Réparé) |
| `#/verify/<pothole_id>?h=` | Anyone with a printed work order | Checks the PDF's QR fingerprint |
| `#/overview` | Officers | KPIs, rain alert, weekly trend, priority queue, street health |
| `#/queue[/<id>]` | Officers | Work queue (views: open, to review, sheets to approve, overdue, urgent, fixed, rejected), CSV / GeoJSON export, case file |
| `#/map[/<id>]` | Officers | Every pothole of the office (canvas renderer, smooth with 5,000+ points) |
| `#/route` | Officers | Today's repair tour (OSRM), print, open in GPS |
| `#/analytics` | Officers | Time to fix by office / governorate / road type, density map, channels, budget table, CSV |
| `#/messages[/<device>]` | Officers | Citizen support inbox |
| `#/assistant` | Officers | Sabeel Assist (answers from the office's own data) |

The case file (`components/PotholePanel.tsx`) shows the photos with the
model's boxes, the priority breakdown, the deadline, the audit log, and every
action: confirm, "not a pothole" (becomes a training label), review / edit /
approve / regenerate the work sheet, download the PDF, mark fixed with a proof
photo (the model re-checks it).

## Run

```bash
npm install
npm run dev            # http://localhost:5173, proxies the API on :8000 (API_URL to change)
npm run typecheck && npm test && npm run build
```

Officer login: paste the office token. In dev (or with `VITE_DEMO_LOGINS=1`)
the login page offers the seed's demo offices (`demo-mun-tunis`,
`demo-dre-tunis`, `demo-ministry`).

## Deploy (static hosting)

`npm run build` produces `dist/`, deployable on Cloudflare Pages or any static
host. Set `VITE_API_BASE_URL` to the API URL at build time, and add the site's
URL to the API's `CORS_ORIGINS`. The service worker (`public/sw.js`) is only
registered in production builds.

## Layout

```
src/
  App.tsx              hash router, login gate, officer shell
  api.ts               typed API client (token in sessionStorage), shared helpers
  i18n.ts              every user-facing label (French; Arabic-ready keys)
  ui.tsx               icons, badges, severity, deadline, priority, photo with boxes
  components/          PotholePanel (case file), charts (line chart, bars)
  pages/               officer pages
  public/              public pages, web report request builder, offline queue
  contract.test.ts     request builder and helpers (Vitest)
```

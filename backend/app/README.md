# Core API

FastAPI + PostgreSQL/PostGIS. It takes citizen reports, runs the vision model
in-process, merges reports into potholes, routes each pothole to the
responsible office, queues the RAG work sheet in the background and serves the
mobile app, the officer dashboard and the public page.

Interactive docs: `http://localhost:8000/docs` (OpenAPI).

## Run locally

```bash
# from the repo root
cp .env.example .env                      # set DATABASE_URL
python -m venv .venv && .venv/Scripts/activate   # (bin/activate on Linux/macOS)
pip install -r backend/app/requirements.txt

python -m uvicorn backend.app.main:app --port 8000 --reload
python -m backend.app.seed                # demo data + demo office tokens
```

The API applies the database migrations itself on startup. You can also run
them by hand: `python -m backend.app.migrate`.

Officer login tokens: `python -m backend.app.scripts.seed_offices` prints one
fresh token per office (stored only as SHA-256). The seed script uses the
predictable demo tokens `demo-<code>`, e.g. `demo-mun-tunis`, `demo-ministry`.
Never use demo tokens on a real deployment.

## Test

```bash
pytest backend/app/tests -q
```

The tests create their own database (`sabeel_test` on the `DATABASE_URL`
server, or `TEST_DATABASE_URL`), migrate it from scratch and truncate it before
every test. They never touch the network: OSM, the RAG service, OSRM and
Open-Meteo are disabled or faked, and OSM answers come from 20 recorded
fixtures (`tests/fixtures/osm_points.json`).

## How a report becomes a repair

```
POST /reports ──> validate (size, JPEG/PNG magic bytes, lat/lon, date)
              ──> vision model on the original photo (score 1-5, confidence, boxes)
              ──> detection gate: no pothole seen -> stored, waits for review
              ──> privacy: EXIF stripped, faces and plates blurred, <= 1600 px
              ──> attach to an open pothole within 5 m (PostGIS ST_DWithin), or create one
              ──> confirmed once 2 *different* phones back it (reports or "I see it too")
background    ──> enrich: OSM road class + ref, governorate, municipality -> office
              ──> sheet: RAG work sheet with checked citations (severity >= 3)
officer       ──> review / edit / approve the sheet -> sheet_sent (PDF with QR fingerprint)
              ──> mark fixed with a proof photo -> the model re-checks the photo
citizens      ──> "well repaired" / "still there" (2 phones reopen it)
daily         ──> SLA escalation to the parent office, rain forecast, priority refresh
```

Nothing slow runs in the request path: `POST /reports` takes about 0.3 s on a
laptop (mostly the model). Sheets and OSM lookups are background jobs.

## Data model

| Table | What it holds |
|---|---|
| `potholes` | One row per physical pothole: status, severity, priority (+ components), road / region / office, sheet, SLA, fix proof and AI check |
| `reports` | One citizen photo: position, sensors, model output (score, confidence, normalised boxes), photo URL, `device_id` |
| `report_events` | Audit log: every status change, sheet edit, approval, escalation, enrichment, confirmation |
| `confirmations` | "I see it too" / "still there" / "well repaired" / "not a pothole", one per device and kind |
| `offices` | Municipalities, regional directorates (DGPC), ministry; parent chain for escalation; token hash |
| `jobs` | Background work (`enrich`, `sheet`) with attempts and backoff |
| `feedback_labels` | Training labels from human decisions (model feedback loop) |
| `geo_cache` | OSM answers keyed by ~30 m cell |
| `messages` | Citizen <-> authority support chat |

Migrations live in `db/migrations/NNN_*.sql`, applied in order and recorded in
`schema_migrations`. Never edit a merged migration; add a new file.

## Status machine

```
new -> confirmed -> sheet_sent -> fixed -> reopened -> (sheet_sent | fixed)
          \_______________________/^   (severity 1-2: confirmed -> fixed, no sheet)
rejected: from any open state
```

- `confirmed`: 2 distinct devices and at least one photo where the model saw a
  pothole, or an officer confirms it by hand.
- `sheet_sent`: **only** through `POST /potholes/{id}/sheet/approve`.
- `fixed`: **only** through `POST /potholes/{id}/fix`, with a proof photo and a note.
- `reopened`: only when `REOPEN_MIN_DEVICES` citizens tap "still there" on a
  fixed pothole, or report it again within `REOPEN_WINDOW_DAYS`.

Anything else answers `409`.

## Endpoints

Citizen (no account; the phone's random `device_id` / `device_report_id` are its proof):

| Route | Purpose |
|---|---|
| `POST /reports` | Multipart report. Idempotent on `device_report_id` (a retry returns `200` with the same report). `detected=false` means no pothole was seen; resend with `force=true` to submit anyway. `direction_deg` and `gps_accuracy_m` optional; `source` = `manual` \| `driving_mode` \| `web` |
| `GET /reports/{device_report_id}` | Tracker: status, timeline, office, first lines of the approved sheet |
| `GET /devices/{device_id}/reports` | Every report this phone sent, with its pothole status |
| `POST /potholes/{id}/confirmations` | `seen` \| `not_fixed` \| `fixed_ok` \| `not_pothole`, within 50 m (GPS accuracy ≤ 40 m) |
| `POST /detect` | Driving mode: scores one frame, stores nothing |
| `GET /map` | Potholes, filters `bbox`, `sev` (`4,5` or `3-5`), `state` (`open`/`fixed`/`all`), `region`, `office` |
| `GET/POST /messages` | The phone's own support thread |

Public (no login, cached 5 min, aggregate only):

| Route | Purpose |
|---|---|
| `GET /public/stats` | Counters, median days to fix, regions (< 5 potholes suppressed), monthly trend, worst streets |
| `GET /public/map` | `{lat, lon, severity, status}` rounded to ~11 m |
| `GET /public/potholes/{id}` | Public pothole card |
| `GET /public/potholes/{id}/verify?h=` | Checks the fingerprint printed on a work-order PDF |

Officer (`Authorization: Bearer <token>`, scoped to the office; the ministry sees all):

| Route | Purpose |
|---|---|
| `GET /auth/me` | Who the token belongs to |
| `GET /authorities/{office_id\|me}/queue` | Sorted to-do list (`sort` = priority/age/severity/deadline; filters `status`, `sev`, `region`, `needs_review`, `sheet_status`, `overdue`; `limit` + `cursor`) |
| `GET /export?format=csv\|geojson` | Same rows and filters as the queue (≤ 10,000) |
| `GET /potholes/{id}` | Full case file: reports, photos, boxes, events, sheet, priority components |
| `PATCH /potholes/{id}` | `confirmed` (manual) or `rejected` (false positive, becomes a training label) |
| `POST /potholes/{id}/fix` | Proof photo + note; the model re-checks the photo |
| `POST /potholes/{id}/feedback` | `not_pothole` / `confirmed_pothole` label |
| `GET/PATCH /potholes/{id}/sheet` | Read / edit the draft (the original is kept) |
| `POST /potholes/{id}/sheet/approve` · `/retry` | Approve (→ `sheet_sent`) or re-queue |
| `GET /potholes/{id}/sheet.pdf` | Work order with citations, OSM link and QR fingerprint |
| `GET /analytics/summary` · `/time-to-fix` · `/hotspots` · `/trend` · `/channels` | Office analytics (`from`, `to`, `office`, `region`) |
| `GET /authorities/{office_id\|me}/route` | Today's repair tour (OSRM, 2-opt fallback) |
| `GET /weather` | 48 h rain forecast and the potholes it puts at risk |
| `POST /assistant` | Sabeel Assist (LLM over the office's live data, data-only fallback) |
| `GET /conversations` · `POST /messages` as `authority` | Support inbox |

Internal (`X-Internal-Token: $INTERNAL_TOKEN`): `POST /internal/run[?daily=true]`,
`/internal/jobs/run`, `/internal/sla/run`, `/internal/weather/run`.

Deprecated, kept for old app builds: `PATCH /reports/{report_id}` (now needs a
token and acts on the report's pothole).

## Priority (why a pothole ranks where it does)

A sum of named points, stored with the pothole so the dashboard can explain
it. Source of truth: [`priority.py`](priority.py).

| Component | Points |
|---|---|
| severity | 10 × severity (1-5) |
| road | 20 national … 6 track (by OSM road class) |
| confirmations | 2.5 per extra citizen, max 10 |
| age | 0.5 per day open, max 15 |
| overdue | +10 past the SLA deadline |
| reopened | +10 citizens say it is still there |
| rain | +10 when ≥ 10 mm is forecast in 48 h and severity ≥ 3 |

## Repair deadlines (SLA)

Source of truth: [`sla.py`](sla.py). MVP values, to validate with a municipal
technical service.

| Severity | Deadline after confirmation | Method |
|---|---|---|
| 5 | 48 h | immediate signage, permanent repair |
| 4 | 7 days | immediate signage, permanent repair |
| 3 | 14 days | hot-mix asphalt repair |
| 1-2 | none | monitor, cold patch at the next round |

`warning` at 80 % of the time, `overdue` at 100 %; at 200 % the daily job
escalates the pothole once to the parent office (municipality → regional
directorate → ministry).

## Privacy (Law 2004-63)

- No account, no name, no phone number. A report carries a random per-install `device_id`.
- Every stored photo is re-encoded (EXIF and GPS tags removed), downscaled and
  has faces and licence plates blurred (OpenCV Haar cascades: best effort,
  see [`privacy.py`](privacy.py)).
- After a sheet is approved, every photo of the pothole is deleted except the
  clearest one, which is kept as a training label.
- Public endpoints never return photos, device ids, sheet text or exact times.
  `tests/test_authorities.py::test_public_payloads_never_contain_private_fields` enforces it.

## Running in production (Cloud Run)

- `STORAGE_BACKEND=supabase` (+ `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`): Cloud
  Run's disk is wiped between instances.
- `JOB_LOOP_INTERVAL_S=0` and an `INTERNAL_TOKEN`: the scheduler workflow calls
  `POST /internal/run` every 10 minutes (CPU is throttled between requests).
- Rate limits are per instance (in memory). Fine for the pilot.
- See [`docs/DEPLOYMENT.md`](../../docs/DEPLOYMENT.md).

## Files

| File | Role |
|---|---|
| `main.py` | App, CORS, lifespan (migrations, model warm-up, job loop) |
| `potholes.py` | Domain logic: attach, confirm, `set_status`, audit, priority |
| `status.py` · `priority.py` · `sla.py` | Pure rules (unit-tested) |
| `jobs.py` | Background queue (`FOR UPDATE SKIP LOCKED`, backoff) |
| `geo/` | OSM enrichment and road-class mapping ([README](geo/README.md)) |
| `auth.py` · `ratelimit.py` · `privacy.py` · `storage.py` | Security, privacy, photos |
| `pdf.py` | Work-order PDF and fingerprint |
| `analytics.py` | Aggregates for analytics, the assistant and the public page |
| `routing.py` · `weather.py` · `sla_job.py` | Route planner, rain forecast, escalation |
| `routers/` | HTTP layer |
| `seed.py` · `scripts/` | Demo data, office tokens, OSM fixture recorder |

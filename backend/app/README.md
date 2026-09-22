# Core API (WP3)

FastAPI service implementing the endpoints and PostGIS schema frozen in
[`docs/Sprint1_Action_Plan.md`](../../docs/Sprint1_Action_Plan.md), Sections 4.1, 4.2 and 4.5.
Wired end-to-end as of the Sprint 1 integration pass: real Postgres/PostGIS storage, the
real vision model, a real HTTP call to the RAG service, and the real <5m dedup check.

## Run locally

```bash
# from the repo root
docker compose up -d db
cp .env.example .env   # adjust DATABASE_URL if not using docker compose

pip install -r backend/app/requirements.txt
uvicorn backend.app.main:app --reload
```

The RAG service must also be running (its own process, see `rag-service/README.md`)
for score >= 3 reports to get a real work sheet -- if it's unreachable, `POST /reports`
still succeeds and the report is simply left at `confirmed` instead of `sheet_sent`
(see "Explicit gaps" below).

- API docs: http://localhost:8000/docs
- Health check (pings the DB): http://localhost:8000/health

## Test

```bash
docker compose up -d db   # tests hit the real database
pytest backend/app/tests -v
```

## What each endpoint actually does

- `POST /reports` — saves the photo to `static/photos/`, runs WP1's `infer()`
  (`ml-training/inference.py`, in-process, see `vision_client.py`), inserts the row,
  runs the real `<5m` dedup check (`dedup.py`, PostGIS `ST_DWithin` against
  `idx_reports_geog`) which promotes a match to `confirmed` and assigns/reuses a
  `cluster_id`, and — if confirmed with `score >= score_threshold_for_sheet` — calls
  the RAG service's `POST /generate` (`rag_client.py`) and stores the resulting
  `sheet_text`/`target_office`, moving status to `sheet_sent`.
- `GET /map?bbox=` — one row per cluster (the latest report in it) plus every
  report not yet matched into a cluster, optionally filtered to a bounding box.
- `GET /reports/{device_report_id}` — the most recent report for that device ID,
  `404` if none exists.
- `PATCH /reports/{report_id}` — the real status state machine (`status.py`,
  `is_valid_transition`) checked against the report's actual current status in
  the database, `404` if the report doesn't exist, `409` on any non-forward
  transition.

## Additive fields beyond the frozen Section 4.1/4.5 contract

`sheet_text` and `target_office` are extra columns (`db/schema.sql`) and extra
optional response fields (`schemas.py`) not in the original frozen shape — added so
`POST /reports` can hand back a generated work sheet immediately, without the mobile
app needing a second round trip. Existing field names and types are unchanged.

## Explicit, accepted gaps

- **No `report_events` history table.** Status changes overwrite `updated_at` in
  place; there's no audit log of every transition yet (Cahier_de_charges.md, Section 7.3).
- **No raw-photo-deletion privacy rule** (cahier des charges Section 8.3) — uploaded
  photos are kept in `static/photos/` indefinitely.
- **RAG failures degrade silently by design.** If the RAG service is down or times
  out, `POST /reports` still returns `201` with the report left at `confirmed` --
  this is intentional (a RAG hiccup must never fail report intake) but means a
  sheet can be silently missing; nothing currently retries it later.
- **The RAG service is a separate HTTP call, not an in-process import** (Core
  API's `requirements.txt` deliberately excludes torch/chromadb/sentence-transformers)
  -- matches the target architecture in the cahier des charges' component diagram,
  even though Sprint 1's Dockerfile comment originally assumed an in-process call.

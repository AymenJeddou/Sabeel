# Core API (WP3)

FastAPI service implementing the Sprint 1 stub endpoints and PostGIS schema frozen in
[`docs/Sprint1_Action_Plan.md`](../../docs/Sprint1_Action_Plan.md), Sections 4.1, 4.2 and 4.5.

## Run locally

```bash
# from the repo root
docker compose up -d db
cp .env.example .env   # adjust DATABASE_URL if not using docker compose

pip install -r backend/app/requirements.txt
uvicorn backend.app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health check (pings the DB): http://localhost:8000/health

## Test

```bash
pytest backend/app/tests -v
```

## What's stubbed vs. real (Sprint 1)

- `POST /reports`, `GET /map`, `GET /reports/{device_report_id}` return hard-coded data
  matching the contract shape exactly — no DB reads/writes yet.
- `PATCH /reports/{report_id}` is wired to the real status state machine
  (`status.py`, `is_valid_transition`) checked against an in-memory fake "current status" —
  returns `409` on any non-forward transition.
- `backend/app/db/schema.sql` creates the real `reports` table + PostGIS extension;
  `db_models.py` mirrors it in SQLAlchemy, ready for Sprint 2 to wire the endpoints to it.

## Deferred to Sprint 2 (not in the frozen Section 4.1 contract)

- `report_events` (status history log) and `sheets` tables (Cahier_de_charges.md, Section 7.3)
- Wiring `POST /reports` to actually insert into `reports` and call WP1's `infer()`
  (`ml-training/inference.py`, already contract-compatible)
- The <5m duplicate-merge check (`ST_DWithin` against the `idx_reports_geog` index)
- Calling WP2's RAG `generate()` in the background when a report is confirmed with score ≥ 3

# FastAPI app — TEMPORARY INSURANCE GLUE (see issue #4)

This is a temporary, minimal glue backend built by Aymen during Sprint 1 so a real
end-to-end mobile demo exists regardless of WP3's own timeline. It wires WP1's
`infer()` (vision model) and WP2's RAG `generate()` (via HTTP) together behind
endpoint shapes that approximate Section 4.5 of `docs/Sprint1_Action_Plan.md`.
Jasseur/Tharaa can replace these files in place once real WP3 work lands — the
endpoint shapes are meant to be a true subset of the frozen contract, not a
divergent one.

## Known, explicitly accepted gaps vs. real WP3

- **SQLite instead of Supabase/PostGIS.** `db.py` + `dedup.py` (plain haversine
  distance) stand in for PostGIS `ST_DWithin`. Fine for a demo, not for
  production scale.
- **No auth.** None at all — matches the MVP's overall "no accounts" rule, but
  also means no rate limiting/abuse protection either.
- **No raw-photo-deletion privacy rule** (Section 8.3 of the cahier des
  charges says raw photos should be deleted once a sheet is made) — not
  implemented here.
- **Synchronous, not background, processing.** `POST /reports` runs vision
  inference and the RAG call inline, so the response may already reflect
  `confirmed`/`sheet_sent` status rather than always `new`/`null` score as
  the illustrative contract example shows — this is additive/faster
  information, not a shape violation.

## Running locally

```bash
cd backend/app
python -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Run from the `backend/` directory (one level up) so the `app` package resolves,
or run `python -m app.main` from `backend/`. Requires `rag-service` running on
`:8001` for the sheet-generation step (see `../../rag-service/README.md`).

## Endpoints

- `POST /reports` — multipart: `device_report_id`, `lat`, `lon`,
  `gps_accuracy_m`, `speed_kmh`, `direction_deg`, `captured_at`, `source`,
  `photo` (file) → `{report_id, device_report_id, status, score}`
- `GET /map` — deduplicated `[{report_id, lat, lon, score, status, cluster_id}]`
- `GET /reports/{device_report_id}` — `{report_id, status, score, sheet_summary?}`
- `PATCH /reports/{report_id}` — body `{"status": "confirmed"|"sheet_sent"|"fixed"}`,
  forward-only, `409` on a backward transition

# Pothole Detection & Management — MVP Tunisia
## Sprint 1 (Week 1) — Action Plan & Integration Contract

Foundations week — every workstream runnable, every handoff shape agreed.

**Team:** Aymen Jeddou · Tharaa Oueslati · Jasseur Chibani · Jed Belhaj Mohamed

---

## 1. This Week's Goal

Sprint 1 of 4. The goal is not features — it's a runnable skeleton for every work package, plus one thing that matters more than any single feature: freezing the exact shape of the data that crosses team boundaries. Agreeing on that now means Sprints 2 and 3 (core build and integration) go fast, because nobody re-writes another person's output format halfway through.

**By Friday:**
- Each WP has something that runs end-to-end (even with fake/mock data)
- The repo has one Dockerfile and a green CI check
- This document's contracts (Section 4) are frozen — changing them after this week means updating three people's code, not one

## 2. What Each Person Delivers This Week

| WP | Owner / Co-owner | This week's job | Concrete deliverable (Friday) |
|---|---|---|---|
| WP1 – AI Model | Tharaa (owner), Jasseur (co) | Collect photos, start training env | ≥400 labelled photos in shared drive; training notebook running end-to-end on 1 pretrained epoch; severity rule (1–5) written as a scoring function spec |
| WP2 – RAG Agent | Aymen (owner), Jed (co) | Collect rules, seed Chroma | `rules_raw/` folder with source law texts; Chroma DB with ≥15 rule chunks embedded and queryable; one handwritten example of `{lat,lon,score} → sheet_text` |
| WP3 – Core API | Jasseur (owner), Tharaa (co) | API skeleton, DB schema | FastAPI repo with 3 stub endpoints returning mock JSON matching the contract below; PostgreSQL live with PostGIS + `reports` table created |
| WP4 – Mobile App | Jed (owner), Aymen (co) | App skeleton, GPS capture | Flutter app that opens, takes a photo, reads GPS/speed/direction, and prints them to console/log — no backend call yet |
| WP-T – Transversal | All | Docker, CI, contracts frozen | One Dockerfile that builds; GitHub Actions workflow green on a no-op test; this document reviewed and signed off by all 4 |

## 3. Detailed Tasks Per Work Package

### WP1 — AI Detection Model (Tharaa · co: Jasseur)
- Pull together the first batch of pothole photos — aim for 400+ this week, 2,000+ by end of build. Split by area (not randomly) so the eventual test set is geographically fair.
- Set up the training environment (YOLOv8n, ONNX export toolchain) and get one pretrained checkpoint fine-tuning, even on the small starter batch — goal is a working pipeline, not accuracy yet.
- Write down the severity scoring rule (1–5) as pseudocode or a short spec — this becomes the `score` field everyone else consumes.
- Do a rough CPU timing test on one inference call, so WP3 knows what latency to plan around.

### WP2 — RAG Agent & Work Sheet (Aymen · co: Jed)
- Gather source rule texts (Local Authorities Code, Law 2018-29, road-type classifications) into a shared folder.
- Split rules into clean chunks and load a first batch into Chroma (embeddings + metadata: road type, rule id, source).
- Draft the sheet-generation prompt and hand-write one example output so WP3 knows what a `sheet_text` actually looks like before the LLM call exists.
- List the safety checks needed later (e.g. "never invent a rule id") — no code needed yet, just the list.

### WP3 — Core API & Geospatial Backend (Jasseur · co: Tharaa)
- Scaffold the FastAPI project with the three stub endpoints in Section 4.5, returning hard-coded JSON matching the contract shape exactly.
- Set up PostgreSQL, enable the PostGIS extension, create the `reports` table using the schema in Section 4.1.
- Stub the status state machine (Section 4.2) as an enum + a validity-check function, even if nothing calls it yet.
- Confirm with WP1/WP2 that stub responses match what their real functions will eventually output.

### WP4 — Mobile App: Citizen & Driving (Jed · co: Aymen)
- Scaffold the Flutter app: a camera screen, a map screen (blank map is fine for now), and basic navigation between them.
- Get GPS, speed, and compass direction reading correctly on a real device — log the values, don't send them anywhere yet.
- Generate and persist a local `device_report_id` (UUID) per report on the phone — this is what lets citizens track status with no login.
- Sketch the offline queue structure (a local list of not-yet-uploaded reports) — implementation can wait, the data shape can't.

### WP-T — Transversal: Integration, CI/CD & Quality (All)
- Write one Dockerfile that can at least build and start an empty FastAPI app — the container everyone's code will eventually live in.
- Set up GitHub Actions: a workflow that runs on every push, even if the only check today is "does it build."
- Agree on the shared settings/config list (Section 4.6) so nobody hardcodes a value someone else needs to change later.
- All four read and sign off on Section 4 of this document before Friday — that's the actual deliverable of this work package this week.

## 4. Shared Data Contracts — Read This Before You Code

These are the exact shapes of data that cross from one person's code into another's. Everything here is **frozen for Sprint 1** — if something needs to change, it's a 5-minute group conversation, not a silent edit.

### 4.1 The Report object (WP1 → WP3 → WP4, and back)

The one object every workstream touches. WP4 creates it, WP1 fills in score/confidence, WP3 stores and serves it, WP2 reads lat/lon/score from it to generate a sheet.

| Field | Type | Example | Notes |
|---|---|---|---|
| `report_id` | UUID string | `"a1b2c3d4-..."` | Server-assigned once the report reaches the API. Never generated on the phone. |
| `device_report_id` | string (UUID) | `"local-9f8e-..."` | Generated on the phone. Lets a citizen check status with no account — never delete or reuse. |
| `photo_url` | string (URL) | `"https://.../r/xyz.jpg"` | Set by the API after upload. Raw photo deleted once the sheet is made (see privacy rules). |
| `lat` / `lon` | float, float | `36.8065, 10.1815` | WGS84 decimal degrees. Always lat first, then lon — never swap the order between services. |
| `gps_accuracy_m` | float | `4.2` | From the phone's location API. Used in de-duplication (WP3). |
| `speed_kmh` | float | `38.5` | 0 if stationary report. |
| `direction_deg` | float, 0–360 | `270.0` | Compass heading — used for "which side of the road." |
| `captured_at` | ISO 8601 string, UTC | `"2026-09-15T10:32:00Z"` | Always UTC, always with the trailing Z — no local timezones in stored data. |
| `source` | enum string | `"manual"` \| `"driving_mode"` | Set by WP4 depending on which flow created the report. |
| `score` | int 1–5, or null | `4` | Null until WP1's model has scored it. |
| `confidence` | float 0–1, or null | `0.87` | From the model. Null until scored. |
| `status` | enum string | `"new"` | See the state machine in 4.2 — only four values are ever valid. |
| `cluster_id` | UUID string, or null | `null` | Set by WP3 once 2+ reports are merged as duplicates (< 5 m apart). |
| `created_at` / `updated_at` | ISO 8601 string, UTC | `"2026-09-15T10:32:05Z"` | Server-set, never sent by the client. |

### 4.2 Status state machine

Exactly four states, and only forward transitions — nothing ever moves backward. WP3 owns enforcing this; WP4 only ever displays the current value.

```
new -> confirmed -> sheet_sent -> fixed
```

- **new** — a report has been received but not yet merged/confirmed with any other report.
- **confirmed** — 2+ reports within 5 m have been merged into one pothole (or a human check confirmed it).
- **sheet_sent** — WP2's RAG agent has generated a work sheet and it has been routed to an office.
- **fixed** — the municipality/DGPC marked the repair complete.

### 4.3 Model inference interface (WP1 → WP3)

WP1 delivers this as a plain function (or a small local HTTP call if it ends up running as its own process) — WP3 calls it, never re-implements the scoring logic.

```
infer(image: bytes) -> {
  "score": int,          # 1-5
  "confidence": float,   # 0-1
  "boxes": [
    { "x": int, "y": int, "w": int, "h": int, "class": "pothole" }
  ],
  "inference_ms": float
}
```

Target: under 250 ms on a normal CPU. If WP1's early tests run slower than that, flag it this week — WP3's timeout/retry logic depends on knowing the real number, not the target number.

### 4.4 RAG agent interface (WP2 → WP3)

```
generate(lat: float, lon: float, score: int, road_type: str = None) -> {
  "sheet_text": str,
  "rule_citations": [
    { "rule_id": str, "source": str, "excerpt": str }
  ],
  "target_office": str,   # e.g. "Municipality" | "DGPC" | "Ministry of Equipment"
  "road_type": str,
  "generated_at": str,    # ISO 8601 UTC
  "generation_ms": float
}
```

Only called by WP3 when score ≥ 3 (matches the use-case diagram's «include» condition). WP2: hand-write one real example this week so WP3 can build the stub against real-looking data instead of guessing.

### 4.5 API endpoints (WP3 → WP4)

| Endpoint | Request | Response |
|---|---|---|
| `POST /reports` | Body: `device_report_id`, photo (multipart), `lat`, `lon`, `gps_accuracy_m`, `speed_kmh`, `direction_deg`, `captured_at`, `source` | `201` → `{ report_id, device_report_id, status: "new", score: null }` |
| `GET /map?bbox=` | Query: bounding box or lat/lon/radius | `200` → `[ { report_id, lat, lon, score, status, cluster_id }, ... ]` — deduplicated, one row per confirmed pothole |
| `GET /reports/{device_report_id}` | Path param only — no login required | `200` → `{ report_id, status, score, sheet_summary? }` — this is what F5's "was it fixed" screen calls |
| `PATCH /reports/{report_id}` | Body: `{ status: "confirmed"\|"sheet_sent"\|"fixed" }` | `200` → `{ report_id, status, updated_at }` — `409` if the transition isn't forward |

### 4.6 Shared config — one list, one source of truth

Put these in one `.env.example` in the repo root this week, even with placeholder values. Nobody hardcodes a value that's on this list.

| Variable | Owner / meaning |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (`postgres://user:pass@host:port/db`) — WP3 owns this |
| `MODEL_PATH` | Path to the exported `pothole_model.onnx` — WP1 sets the filename convention |
| `CHROMA_DB_PATH` | Path to the rules vector store — WP2 owns |
| `LLM_ENDPOINT` / `LLM_API_KEY` | Wherever the free-tier LLM call goes (Hugging Face inference, etc.) |
| `MAX_DEDUP_DISTANCE_M` | 5 — the de-duplication radius, must match across WP3 and the goals table |
| `SCORE_THRESHOLD_FOR_SHEET` | 3 — the minimum score that triggers WP2's `generate()` call |
| `PORT` / `CLOUD_RUN_SERVICE_NAME` | Deployment — WP-T owns |

## 5. Recommendations

- **Freeze the contracts, not the code.** It's fine if the real implementation behind an endpoint is a stub returning fake JSON this week — what can't change without a group conversation is the shape of that JSON.
- **Build against mocks, not against each other's unfinished work.** WP4 should be able to build the whole app against WP3's stub endpoints without ever waiting for WP1's model to be ready.
- **Use exactly the field names in Section 4** — no local renaming ("lng" vs "lon", "conf" vs "confidence"). A single renamed field is the most common source of integration bugs in a 4-person build.
- **All timestamps UTC, ISO 8601, always with a trailing Z.** Decide this once so nobody debugs a "report from the future" bug in Sprint 3.
- **Keep `.env.example` (Section 4.6) up to date** the moment you add a new setting — it's the fastest way for someone else to run your service locally.
- **Short daily check-in (10 minutes, even async in chat)** beats a long Friday meeting — the goal this week is catching a contract mismatch on Tuesday, not Friday.
- **Commit early and often against the CI pipeline** once it's green — "no broken main" only works if everyone is actually pushing to it this week, not saving up changes for Sprint 2.

## 6. End-of-Week Definition of Done — Sprint 1

- [ ] Photo collection underway (400+ photos), training pipeline runs end-to-end on a small sample
- [ ] Chroma seeded with rule chunks; one hand-written sheet example shared with WP3
- [ ] FastAPI stub endpoints live and matching Section 4.5 exactly; PostgreSQL + PostGIS schema created
- [ ] Flutter app opens, captures a photo, and logs GPS/speed/direction correctly on a real device
- [ ] One Dockerfile builds; GitHub Actions runs green on every push
- [ ] Sections 4.1–4.6 of this document reviewed and agreed by all four team members

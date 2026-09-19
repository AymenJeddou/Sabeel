# RoadScan — Pothole Detection & Management System (Tunisia)

A mobile app, a small AI model, a map, and a simple RAG agent — an MVP that turns a citizen's photo of a pothole into a located, graded, and routed repair work order.

**Project length:** 4 weeks · **Budget:** 0 TND (free-tier cloud services only)
**Full spec:** [`docs/Cahier_de_charges.md`](docs/Cahier_de_charges.md) · **Current sprint plan:** [`docs/Sprint1_Action_Plan.md`](docs/Sprint1_Action_Plan.md)

## What it does

1. **Report** — a citizen (or a phone in hands-free driving mode) takes a photo; GPS, time, direction, and speed are captured with it.
2. **Detect & score** — a YOLOv8n model grades the pothole 1–5 for severity.
3. **Confirm** — two reports within 5 m of each other merge into one confirmed pothole.
4. **Write the work sheet** — for confirmed potholes scoring ≥ 3, a RAG agent looks up the real road-type rules and drafts a work order, citing its sources, then routes it to the right office (Municipality / DGPC / Ministry of Equipment).
5. **Track** — a live map with filters, a per-office priority list, and status updates back to the citizen.

## Architecture

| Component | Folder | Stack |
|---|---|---|
| Mobile app | [`mobile/`](mobile) | Flutter — capture, map, offline queue, driving mode |
| Core API | [`backend/app`](backend/app) | FastAPI + Supabase/PostGIS — reports, map, status |
| Vision service | [`backend/vision`](backend/vision) / [`ml-training/`](ml-training) | YOLOv8n, ONNX Runtime (CPU) |
| RAG service | [`rag-service/`](rag-service) | Chroma + free LLM (Hugging Face) — work-sheet generation |

## Team & roles

| Work package | Owner | Co-owner |
|---|---|---|
| WP1 — AI detection model | [@tharaaoueslati-lang](https://github.com/tharaaoueslati-lang) | [@jasseurchibani](https://github.com/jasseurchibani) |
| WP2 — RAG agent & work sheet | [@AymenJeddou](https://github.com/AymenJeddou) | [@JedBelhaj](https://github.com/JedBelhaj) |
| WP3 — Core API & geospatial backend | [@jasseurchibani](https://github.com/jasseurchibani) | [@tharaaoueslati-lang](https://github.com/tharaaoueslati-lang) |
| WP4 — Mobile app (citizen & driving mode) | [@JedBelhaj](https://github.com/JedBelhaj) | [@AymenJeddou](https://github.com/AymenJeddou) |

Task-level breakdowns and the shared data contracts between work packages live in [`docs/Sprint1_Action_Plan.md`](docs/Sprint1_Action_Plan.md). Each sprint's tasks are tracked as GitHub Issues, one per work package.

## Sprint schedule

- **Sprint 1** — foundations (skeleton for every work package, data contracts frozen). **Ends Monday, September 21.**
- Sprints 2–3 — core build and integration.
- Sprint 4 — hardening, final checklist, live demo.

## Workflow — how we work (Agile / Scrum)

This repo follows a strict branch/PR workflow. It applies to everyone, including maintainers.

1. **No direct pushes to `main` or `dev`.** All changes go through a pull request and a review, no exceptions.
2. **Branch from `dev`, not `main`.** Name your branch by type and topic, e.g. `feature/wp2-rag-chunking`, `fix/api-dedup-bug`, `chore/ci-cache`.
3. **Open your PR against `dev`.** `dev` is the integration branch — this is where all work packages meet.
4. **`main` is protected and reserved for stable, reviewed, demo-ready code only.** `dev` merges into `main` only at the end of a sprint, once the sprint's Definition of Done is met.
5. **Every PR needs at least one review** from another team member (ideally your work package's co-owner) before merging.
6. **Keep PRs small and scoped** to one task or one issue — easier to review, easier to revert.
7. **Reference the issue you're closing** in your PR description (e.g. `Closes #4`).
8. **CI must be green before merge.** A broken `dev` blocks everyone.
9. **Use exactly the field names and shapes defined in the data contracts** (`docs/Sprint1_Action_Plan.md`, Section 4) — a locally renamed field is the most common source of integration bugs across work packages.
10. **All timestamps are UTC, ISO 8601, with a trailing `Z`.**

### Typical flow

```
git checkout dev
git pull
git checkout -b feature/<short-description>
# ... work, commit ...
git push -u origin feature/<short-description>
# open a PR: base = dev, compare = feature/<short-description>
```

## Getting started

Each component has its own README with setup instructions: [`mobile/README.md`](mobile/README.md), [`backend/app/README.md`](backend/app/README.md), [`backend/vision/README.md`](backend/vision/README.md), [`ml-training/README.md`](ml-training/README.md), [`rag-service/README.md`](rag-service/README.md). Shared environment variables are listed in [`.env.example`](.env.example).

# Sabeel · Espace Autorités

Web dashboard for the municipality / DGPC: overview KPIs, live map, reports table
(CSV export), citizen support inbox and **Sabeel Assist**, an LLM assistant grounded
on the report database (`POST /assistant` in the Core API).

```
npm install
npm run dev          # http://localhost:5173, proxies the API from :8002
npm run build        # type-check + production bundle
```

Needs the Core API on :8002 (`backend/app`) and, for LLM answers, the RAG service
on :8001. Demo data: `python -m backend.app.seed` from the repo root.

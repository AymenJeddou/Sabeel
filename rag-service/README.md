# RAG service — own Dockerfile, own deploy, exposes generate() as POST /generate

WP2 deliverable (owner: Aymen, co-owner: Jed — see issue #3). Turns a confirmed,
serious pothole (score >= 3) into a work order: retrieves the matching road-type
rules from a local Chroma store and has an LLM write the sheet, citing only
rules it was actually shown. Falls back to a deterministic template (which
stitches real retrieved excerpts directly) whenever the LLM call fails or its
citations don't check out — `generate()` never fabricates a rule and never
raises.

## Setup

```bash
cd rag-service
python -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements.txt
copy .env.example .env   # then fill in HF_API_TOKEN
python -m ingestion.build_index   # seeds Chroma from rules_real/ + rules_placeholder/
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Rules

- [`rules_real/`](rules_real) — actually-sourced Tunisian legal citations (road
  classification / jurisdiction — who a work order gets routed to). See its
  README for provenance and known gaps.
- [`rules_placeholder/`](rules_placeholder) — MVP engineering-practice
  placeholders (repair urgency/method) — clearly not real law, see its README.

Re-run `python -m ingestion.build_index` any time a rule file changes; it wipes
and rebuilds the Chroma collection from scratch, so it's always safe to re-run.

## API

- `POST /generate` — body `{lat, lon, score, road_type?}` → `{sheet_text,
  rule_citations, target_office, road_type, generated_at, generation_ms}`
- `GET /health` — `{status, chunks_indexed}`

## Safety checks implemented

- Per-call citation allowlist (only chunks actually retrieved for *this*
  call are citable — never the whole DB).
- Similarity floor (cosine >= 0.35) before any chunk is eligible to be shown.
- All-or-nothing citation validation — any invalid or missing citation
  discards the entire LLM output in favor of the template fallback.
- `generate()` never lets an exception escape — any internal failure returns
  a safe "manual review recommended" response instead.

See `tests/sample_calls.md` for a worked example.

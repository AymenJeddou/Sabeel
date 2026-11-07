# RAG service

Turns a confirmed pothole (severity ≥ 3) into a work order that **cites real
texts only**. It retrieves the matching rules from a local Chroma index and
has an LLM write the sheet; every citation is checked against what the LLM
was shown, and any doubt falls back to a deterministic template built from
the rules' own text. `generate()` never invents a rule and never raises.

The Core API calls it from a background job (never inside `POST /reports`)
and passes the office it routed the pothole to, the address and the road
owner (`municipal` / `state`, from OpenStreetMap).

## Setup

```bash
cd rag-service
python -m venv .venv && .venv\Scripts\activate          # Windows
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
copy .env.example .env                                    # LLM credentials
python -m ingestion.build_index                           # also done at startup if the index is empty
uvicorn app.main:app --port 8001 --reload
```

The Docker image builds the index (and downloads the embedding model) at
build time, so a cold start only loads it.

## LLM provider

Any OpenAI-compatible chat endpoint works:

| Provider | Settings |
|---|---|
| Hugging Face router (default) | `HF_API_TOKEN`, `HF_MODEL_PRIMARY`, `HF_MODEL_BACKUP` |
| Groq (free tier) | `LLM_BASE_URL=https://api.groq.com/openai/v1`, `LLM_API_KEY`, `LLM_MODEL=llama-3.1-8b-instant`, `LLM_MODEL_BACKUP=llama-3.3-70b-versatile` |
| OpenRouter (free models) | `LLM_BASE_URL=https://openrouter.ai/api/v1`, `LLM_API_KEY`, `LLM_MODEL=<model id>` |

Status on 2026-11-07: the project's Hugging Face token answers **402 Payment
Required** (monthly free credits used up), so every sheet currently comes from
the template. The template is a complete work order (competent office and its
legal basis, urgency, repair method, signage), but it is not written by a model.

## Rule corpus (`rules_real/`)

15 rules, all with a real source. No placeholder rule is left (Sprint 1 had 15).

| File | What it covers | Source |
|---|---|---|
| `loi_2018_29_ccl.yaml` | Municipal road domain (who repairs city streets) | Loi organique n°2018-29, Code des Collectivités Locales, art. 69 |
| `loi_86_17_classification.yaml` | National / regional / local roads belong to the State (DGPC), including national roads crossing towns; motorways (Tunisie Autoroutes); DGPC mandate | Loi n°86-17 du 7 mars 1986; mehat.gov.tn; tunisieautoroutes.tn |
| `fhwa_pothole_repair_manual.yaml` | Repair methods (throw-and-roll, semi-permanent, spray injection, edge seal), urgency, signage, hot vs cold mix | FHWA-RD-99-168, *Materials and Procedures for Repair of Potholes in Asphalt-Surfaced Pavements — Manual of Practice*, Wilson & Romine, 1999 (US public domain), translated into French; the English original is kept in each rule's `note` |

**Legal watch.** Business News (1 Oct 2026) reports that décret-loi n°4 du
30 septembre 2026 on municipal councils repeals Law 2018-29, with effect after
the next municipal elections. Until then the 2018 code applies; re-check
article 69's equivalent in the new text and update `loi_2018_29_ccl.yaml`.

Rule fields: `rule_id`, `text`, `source`, `road_type` (one of the five road
types, or `all` for method rules), `target_office` (`Municipality`, `DGPC`,
`Ministry of Equipment`, or `any` for method rules), `severity_min`, `note`.
The indexer derives `jurisdiction` (`municipal` / `state` / `any`) from the office.

Re-run `python -m ingestion.build_index` after editing a rule: it rebuilds the
collection from scratch.

## Retrieval

1. The query is built from the severity: who owns the road, the repair method
   that fits (semi-permanent from 3, quick patch below), urgency and signage from 4.
2. Chroma filter: this road type or `all`, `severity_min ≤ score`, and only the
   road owner's legal rules (when the Core API knows the owner).
3. Similarity floor 0.35, top 8, then `select_shown()` keeps up to 4 chunks,
   always including the best jurisdiction rule and the right method.

## API

- `POST /generate`: `{lat, lon, score, road_type?, office_name?, address?, jurisdiction?}` →
  `{sheet_text, rule_citations, target_office, target_office_label, road_type, generated_at, generation_ms}`
- `POST /chat`: free-form completion used by Sabeel Assist (the Core API builds the prompt)
- `GET /health`: `{status, chunks_indexed}`

## Safety checks

- Per-call citation allowlist: only the chunks shown for this call are citable.
- All-or-nothing validation: one unknown or missing citation discards the LLM output.
- Wall-clock timeout on every LLM call (`LLM_TIMEOUT_S`, default 20 s).
- `generate()` catches everything and returns a "manual review" sheet instead.

Tests (`pytest tests`) need no network, no Chroma and no LLM. A worked
example is in [`tests/sample_calls.md`](tests/sample_calls.md).

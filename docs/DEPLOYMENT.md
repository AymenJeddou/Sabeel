# Deployment (0 TND)

| Piece | Where | Free tier |
|---|---|---|
| Core API (`Dockerfile`) | Google Cloud Run `sabeel-api` | 2 M requests, 180,000 vCPU·s / month |
| RAG service (`rag-service/Dockerfile`) | Cloud Run `sabeel-rag` (private) | same |
| Database | Supabase PostgreSQL (PostGIS) | 500 MB |
| Photos | Supabase Storage bucket `photos` (public read) | 1 GB |
| Web app (dashboard, public page, PWA) | Cloudflare Pages `sabeel` | unlimited static requests |
| Background jobs, SLA, weather | GitHub Actions `scheduler.yml` every 10 min | 2,000 min / month |
| LLM | Groq or OpenRouter free tier (or a Hugging Face token with credits) | rate-limited |
| Android app | GitHub release asset from `mobile-apk.yml` | free |

Every push to `main` runs `.github/workflows/deploy.yml`. Each job is
skipped until its secrets exist, so the workflow stays green before setup.

## One-time setup

1. **Supabase**: create a project. In the SQL editor run
   `create extension if not exists postgis;`. Copy the *Session pooler*
   connection string and change `postgresql://` to `postgresql+asyncpg://`.
   In Storage, create a **public** bucket `photos`. Copy the project URL and the
   `service_role` key.
2. **Google Cloud**: create a project, enable Cloud Run, Artifact Registry and
   Secret Manager, create an Artifact Registry Docker repository `sabeel` in
   `europe-west1`, and a service account with the roles Cloud Run Admin,
   Artifact Registry Writer, Service Account User and Secret Manager Secret
   Accessor. Download its JSON key.
3. **Secrets in Google Secret Manager**: `sabeel-database-url`,
   `sabeel-supabase-url`, `sabeel-supabase-key`, `sabeel-internal-token` (any
   long random string), `sabeel-hf-token`, `sabeel-llm-key`.
4. **GitHub repository secrets**: `GCP_SA_KEY` (the JSON key), `GCP_PROJECT`,
   `INTERNAL_TOKEN` (same value as `sabeel-internal-token`),
   `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
5. **GitHub repository variables**: `API_URL` (the `sabeel-api` URL, known
   after the first deploy), `RAG_URL` (the `sabeel-rag` URL), `WEB_URL` (the
   Pages URL, e.g. `https://sabeel.pages.dev`), `LLM_BASE_URL` and `LLM_MODEL`
   (e.g. `https://api.groq.com/openai/v1` and `llama-3.1-8b-instant`),
   optionally `DEMO_LOGINS=1` for a jury demo.
6. **Cloudflare**: create a Pages project named `sabeel` (direct upload).
7. **Offices**: once the API is up, create the offices and their tokens:
   `DATABASE_URL=<supabase> python -m backend.app.scripts.seed_offices`.
   Give each office its own token; never use `--demo` in production.
8. **Private RAG service**: `sabeel-rag` is deployed with
   `--no-allow-unauthenticated`; grant the API's runtime service account the
   Cloud Run Invoker role on it, or for the pilot redeploy it with
   `--allow-unauthenticated` (it holds no data, only the public rule corpus).

The API applies its database migrations on startup. On Cloud Run it runs
with `JOB_LOOP_INTERVAL_S=0`: the scheduler workflow calls
`POST /internal/run` every 10 minutes (jobs) and once a day around 05:00 UTC
with `daily=true` (SLA escalation, rain forecast). Rate limits are per
instance.

## Check a deployment

```bash
python -m backend.app.scripts.e2e_smoke --api https://<api> --token <ministry token> --internal <INTERNAL_TOKEN>
```

It walks the whole demo path (two phones, confirmation, routing, sheet,
approval, tracker, PDF, QR, fix with AI check, public stats) and stops at the
first failure.

## Local stack

```bash
docker compose up -d            # db (PostGIS) + api + rag-service
python -m backend.app.seed      # demo data; office logins demo-mun-tunis, demo-dre-tunis, demo-ministry
cd dashboard && npm run dev     # http://localhost:5173
```

Without Docker: PostgreSQL 16 + PostGIS, `uvicorn backend.app.main:app
--port 8000` from the repo root, `uvicorn app.main:app --port 8001` in
`rag-service/`.

# Deployment (0 TND)

Two ways. **Option A is the one to use**: two free accounts, no credit
card, no scheduler, about 30 minutes. Option B (Google Cloud Run) is kept for
a larger, auto-scaling deployment.

## Option A: one Hugging Face Space + Supabase (recommended)

```
phones, browsers ──> Hugging Face Space (one container, free, 2 vCPU / 16 GB)
                      ├─ Core API + the built web app on port 7860
                      ├─ RAG service on 127.0.0.1:8001
                      └─ job loop: sheets, OSM, daily SLA + rain forecast
                               │
                     Supabase (free): PostgreSQL + PostGIS, photo storage
                     Groq (free): the LLM for work sheets and Sabeel Assist
```

The web app is served by the API itself (same address, no CORS to configure),
and the background jobs run inside the container, so there is no scheduler
to set up. A free Space sleeps after 48 h without visitors and wakes on the
next visit (about a minute).

### 1. Supabase: database and photos (10 min)

1. Sign up at [supabase.com](https://supabase.com) (GitHub login is fine) and **New project**. Pick the Frankfurt or Paris region and keep the database password.
2. **SQL Editor**, run: `create extension if not exists postgis;`
3. **Connect** (top bar) → *Session pooler* → copy the URI. Replace
   `postgresql://` with `postgresql+asyncpg://` and put your password in it. This is `DATABASE_URL`.
4. **Storage** → *New bucket* → name `photos`, tick **Public bucket**.
5. **Project Settings → API**: copy the *Project URL* (`SUPABASE_URL`) and the
   `service_role` key (`SUPABASE_SERVICE_KEY`; keep it secret).

The API creates all tables itself on first start.

### 2. Hugging Face Space: the app (10 min)

1. Sign up at [huggingface.co](https://huggingface.co) → **New Space** → name
   `sabeel`, SDK **Docker** (blank template), hardware **CPU basic (free)**,
   visibility Public.
2. Space **Settings → Variables and secrets**, add as **secrets**:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | from Supabase step 3 |
   | `SUPABASE_URL` | from step 5 |
   | `SUPABASE_SERVICE_KEY` | from step 5 |
   | `LLM_API_KEY` | your Groq key |
   | `INTERNAL_TOKEN` | any long random string |

   and as **variables**: `PUBLIC_BASE_URL` = `https://<your-hf-name>-sabeel.hf.space`.
3. Hugging Face **Settings → Access Tokens** → new token with **write** role.
4. On GitHub (repo **Settings → Secrets and variables → Actions**): secret
   `HF_TOKEN` = that token, variable `HF_SPACE` = `<your-hf-name>/sabeel`.
5. Merge `dev` into `main` (or run **Actions → Deploy (Hugging Face Space) →
   Run workflow**). The workflow uploads the code; the Space builds the
   image (about 10 minutes the first time) and starts.

Without GitHub Actions, the same upload from your PC:

```bash
pip install huggingface_hub && huggingface-cli login
python deploy/huggingface/upload.py <your-hf-name>/sabeel
```

### 3. Offices and demo data (5 min)

From your PC, against the Supabase database:

```bash
set DATABASE_URL=postgresql+asyncpg://...      (the Supabase URL)
python -m backend.app.scripts.seed_offices      # real tokens, printed once: give each office its own
python -m backend.app.seed                      # optional: the demo potholes (uses demo-<code> tokens)
```

For a jury demo, `python -m backend.app.seed` gives the logins
`demo-mun-tunis`, `demo-dre-tunis` and `demo-ministry`. Don't use them for real
offices.

### 4. Check it

```bash
python -m backend.app.scripts.e2e_smoke --api https://<your-hf-name>-sabeel.hf.space --token demo-ministry
```

- Public page: `https://<your-hf-name>-sabeel.hf.space/`
- Report from a phone: `…/#/report` (add it to the home screen)
- Authorities: `…/#/overview`

### 5. The Android app

GitHub repo variable `API_BASE_URL` = the Space URL, then publish a release
(**Releases → Draft a new release**, tag `v1.0.0`). The **Mobile APK**
workflow builds `sabeel.apk` and attaches it to the release; the public
page's "Application Android" button links there.

### What it costs and its limits

All free: the Space (2 vCPU, 16 GB RAM), Supabase (500 MB database, 1 GB
photos), Groq (rate-limited to ~2-3 work sheets per minute, which the job
queue absorbs). Limits for a pilot: one container (no auto-scaling), and the
48 h sleep (the first visit after a quiet weekend takes about a minute).

---

## Option B: Google Cloud Run (auto-scaling)

Needs a Google Cloud billing account (a card, even if usage stays within the
free tier) and more setup. `.github/workflows/deploy.yml` deploys `sabeel-api`
and `sabeel-rag` to Cloud Run and the web app to Cloudflare Pages on each push
to `main`; `.github/workflows/scheduler.yml` calls `POST /internal/run` every
10 minutes, because Cloud Run throttles CPU between requests
(`JOB_LOOP_INTERVAL_S=0`).

1. Supabase as in Option A.
2. Google Cloud: enable Cloud Run, Artifact Registry and Secret Manager; create
   the Docker repository `sabeel` in `europe-west1`; create a service account
   (Cloud Run Admin, Artifact Registry Writer, Service Account User, Secret
   Manager Secret Accessor) and download its JSON key.
3. Secret Manager: `sabeel-database-url`, `sabeel-supabase-url`,
   `sabeel-supabase-key`, `sabeel-internal-token`, `sabeel-hf-token`, `sabeel-llm-key`.
4. GitHub secrets: `GCP_SA_KEY`, `GCP_PROJECT`, `INTERNAL_TOKEN`,
   `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`. Variables: `API_URL`,
   `RAG_URL`, `WEB_URL`, `LLM_BASE_URL` (`https://api.groq.com/openai/v1`),
   `LLM_MODEL` (`qwen/qwen3.8-27b`).
5. Cloudflare Pages project `sabeel` (direct upload).
6. `sabeel-rag` is private: give the API's service account the Cloud Run
   Invoker role on it.

## Local stack

```bash
docker compose up -d            # db (PostGIS) + api + rag-service
python -m backend.app.seed      # demo data
cd dashboard && npm run dev     # http://localhost:5173
```

Or the Space image locally: `docker build -f deploy/huggingface/Dockerfile -t sabeel .`
then `docker run -p 7860:7860 --env-file .env sabeel`.

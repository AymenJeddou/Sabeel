# Sabeel in ONE container, for a free Hugging Face Space (Docker SDK):
# Core API + RAG service + the built web app (dashboard, public page, PWA).
# The database and the photos live in Supabase. See docs/DEPLOYMENT.md.
#
# Build context = repository root:  docker build -f deploy/huggingface/Dockerfile .

# 1. Web app, built to call the API on the same origin.
FROM node:22-slim AS web
WORKDIR /web
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
ARG VITE_DEMO_LOGINS=""
ENV VITE_API_BASE_URL="" VITE_DEMO_LOGINS=$VITE_DEMO_LOGINS
RUN npm run build

# 2. Python: Core API + RAG (CPU-only torch keeps the image ~2 GB smaller).
FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY backend/app/requirements.txt api-requirements.txt
COPY rag-service/requirements.txt rag-requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r api-requirements.txt -r rag-requirements.txt

COPY backend/__init__.py backend/__init__.py
COPY backend/app backend/app
COPY ml-training/inference.py ml-training/severity_scoring.py ml-training/
COPY ml-training/models ml-training/models
COPY rag-service/app rag-service/app
COPY rag-service/ingestion rag-service/ingestion
COPY rag-service/rules_real rag-service/rules_real
COPY --from=web /web/dist web
COPY deploy/huggingface/start.sh start.sh

# Embedding model + rule index baked into the image: no download at start.
ENV HF_HOME=/app/.hf CHROMA_DB_PATH=/app/rag-service/chroma_db
RUN cd rag-service && python -m ingestion.build_index \
 && chown -R user:user /app && chmod +x /app/start.sh

USER user
# Defaults for this layout; secrets (DATABASE_URL, SUPABASE_*, LLM_API_KEY)
# come from the Space settings.
ENV PORT=7860 \
    SERVE_WEB_DIR=/app/web \
    RAG_SERVICE_URL=http://127.0.0.1:8001 \
    STORAGE_BACKEND=supabase \
    JOB_LOOP_INTERVAL_S=20 \
    ONNX_INTRA_OP_THREADS=2 \
    LLM_BASE_URL=https://api.groq.com/openai/v1 \
    LLM_MODEL=qwen/qwen3.8-27b \
    LLM_MODEL_BACKUP=qwen/qwen3.8-27b \
    PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["/app/start.sh"]

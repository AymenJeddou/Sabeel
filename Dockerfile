# Core API (WP3) image. Vision (WP1) is an in-process call: only inference.py,
# severity_scoring.py and the ONNX model are copied from ml-training/. The RAG
# service (WP2) is a separate image (rag-service/Dockerfile), never imported here.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY backend/__init__.py ./backend/__init__.py
COPY backend/app ./backend/app
COPY ml-training/inference.py ml-training/severity_scoring.py ./ml-training/
COPY ml-training/models ./ml-training/models
# Run as an unprivileged user; it only needs to write local photos (dev storage backend).
RUN useradd --create-home --uid 1000 sabeel  && mkdir -p backend/app/static/photos && chown -R sabeel backend/app/static/photos
USER sabeel
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
# Migrations run on startup (main.py lifespan).
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]

# Runs the Core API (WP3) only. Vision (WP1) is an in-process function call --
# ml-training/ is copied in for its ONNX model + inference.py. RAG (WP2) is a
# separate HTTP service (its own Dockerfile in rag-service/), never imported
# here, to keep torch/chromadb/sentence-transformers out of this image.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY backend/app ./backend/app
COPY ml-training/inference.py ml-training/severity_scoring.py ./ml-training/
COPY ml-training/models ./ml-training/models
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]

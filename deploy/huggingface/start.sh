#!/bin/sh
# Starts the RAG service (internal, port 8001) and the Core API + web app
# (public, $PORT). If either process dies, the container exits and the Space
# restarts it.
set -e
cd /app/rag-service
uvicorn app.main:app --host 127.0.0.1 --port 8001 &
RAG=$!
cd /app
uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-7860}" --proxy-headers --forwarded-allow-ips='*' &
API=$!
# Exit as soon as one of the two stops.
while kill -0 "$RAG" 2>/dev/null && kill -0 "$API" 2>/dev/null; do sleep 5; done
exit 1

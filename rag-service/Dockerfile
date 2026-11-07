FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ingestion ./ingestion
COPY rules_real ./rules_real

# Build the Chroma index (and download the embedding model) at image-build
# time, not on every cold start (issue #11). The index is rebuilt whenever a
# rule file changes, because that invalidates this layer.
ENV CHROMA_DB_PATH=/app/chroma_db HF_HOME=/app/.hf
RUN python -m ingestion.build_index

EXPOSE 8001
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]

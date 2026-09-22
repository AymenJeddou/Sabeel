FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ingestion ./ingestion
COPY rules_real ./rules_real
COPY rules_placeholder ./rules_placeholder

EXPOSE 8001

# Idempotent -- rebuilds the Chroma collection from rules_real/ + rules_placeholder/
# on every container start, so an updated rule file always takes effect.
CMD ["sh", "-c", "python -m ingestion.build_index && uvicorn app.main:app --host 0.0.0.0 --port 8001"]

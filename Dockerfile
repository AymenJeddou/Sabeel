# Draft for WP-T review. Runs the Core API (WP3) only — vision/RAG are function calls
# inside this process for the MVP (Cahier_de_charges.md, Section 7.2).
FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY backend/app ./backend/app
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]

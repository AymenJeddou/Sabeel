"""RAG service -- exposes generate() as POST /generate (per rag-service/README.md)."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from . import config
from .pipeline import generate
from .retrieval import collection_count
from .schemas import GenerateRequest, GenerateResponse, HealthResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RoadScan RAG Service")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", chunks_indexed=collection_count())


@app.post("/generate", response_model=GenerateResponse)
def generate_endpoint(req: GenerateRequest) -> GenerateResponse:
    result = generate(lat=req.lat, lon=req.lon, score=req.score, road_type=req.road_type)
    return GenerateResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)

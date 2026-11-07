"""RAG service -- exposes generate() as POST /generate (per rag-service/README.md)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import config
from .embeddings import get_model
from .generation import call_llm
from .pipeline import generate
from .retrieval import collection_count
from .schemas import GenerateRequest, GenerateResponse, HealthResponse

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Eagerly load the embedding model so the first real request doesn't pay
    # for HF Hub metadata round-trips on top of the LLM call's own timeout.
    get_model()
    if collection_count() == 0:  # e.g. a fresh volume: build the index once
        from ingestion.build_index import main as build_index

        build_index()
    yield


app = FastAPI(title="Sabeel RAG Service", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", chunks_indexed=collection_count())


@app.post("/generate", response_model=GenerateResponse)
def generate_endpoint(req: GenerateRequest) -> GenerateResponse:
    result = generate(lat=req.lat, lon=req.lon, score=req.score, road_type=req.road_type,
                      office_name=req.office_name, address=req.address, jurisdiction=req.jurisdiction)
    return GenerateResponse(**result)


class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat")
def chat_endpoint(req: ChatRequest) -> dict:
    """Free-form LLM call for the dashboard assistant (the Core API builds the
    prompt from its database). Same bounded call as /generate, with the larger
    model: the 8B one mislabels severities when reasoning over ~30 rows."""
    from .generation import LLMRateLimited

    try:
        content = call_llm(req.prompt, timeout_s=40, model=config.HF_MODEL_BACKUP, max_tokens=800)
    except LLMRateLimited as exc:
        raise HTTPException(status_code=503, detail=str(exc), headers={"Retry-After": f"{exc.retry_after_s:.0f}"}) from exc
    if content is None:
        raise HTTPException(status_code=503, detail="LLM unavailable")
    from .pipeline import clean_llm_text

    return {"content": clean_llm_text(content)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)

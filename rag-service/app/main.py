"""RAG service -- exposes generate() as POST /generate (per rag-service/README.md)."""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import config
from .embeddings import get_model
from .generation import call_llm
from .pipeline import generate
from .retrieval import collection_count
from .schemas import GenerateRequest, GenerateResponse, HealthResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RoadScan RAG Service")


@app.on_event("startup")
def on_startup() -> None:
    # Eagerly load the embedding model so the first real request doesn't pay
    # for HF Hub metadata round-trips on top of the LLM call's own timeout.
    get_model()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", chunks_indexed=collection_count())


@app.post("/generate", response_model=GenerateResponse)
def generate_endpoint(req: GenerateRequest) -> GenerateResponse:
    result = generate(lat=req.lat, lon=req.lon, score=req.score, road_type=req.road_type)
    return GenerateResponse(**result)


class ChatRequest(BaseModel):
    prompt: str


@app.post("/chat")
def chat_endpoint(req: ChatRequest) -> dict:
    """Free-form LLM call for the dashboard assistant (the Core API builds the
    prompt from its database). Same bounded call as /generate, longer budget."""
    content = call_llm(req.prompt, timeout_s=25)
    if content is None:
        raise HTTPException(status_code=503, detail="LLM unavailable")
    return {"content": content}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)

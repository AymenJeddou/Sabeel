"""HTTP client for the RAG service's POST /generate (a real service boundary,
not an in-process import -- keeps torch/chromadb/sentence-transformers out of
the Core API's own dependency footprint)."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)


async def generate(lat: float, lon: float, score: int, road_type: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Returns the RAG service's response dict, or None on any failure --
    callers must never let a RAG hiccup fail the whole POST /reports call."""
    payload: dict[str, Any] = {"lat": lat, "lon": lon, "score": score}
    if road_type:
        payload["road_type"] = road_type

    try:
        async with httpx.AsyncClient(timeout=settings.rag_timeout_s) as client:
            response = await client.post(f"{settings.rag_service_url}/generate", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001 - RAG failures must never surface as a 500 here
        logger.warning("RAG service call failed: %s", exc)
        return None


async def chat(prompt: str) -> Optional[str]:
    """Free-form LLM answer via the RAG service's POST /chat, or None on any
    failure -- the assistant then falls back to a data-only answer."""
    try:
        async with httpx.AsyncClient(timeout=settings.rag_timeout_s + 15) as client:
            response = await client.post(f"{settings.rag_service_url}/chat", json={"prompt": prompt})
        response.raise_for_status()
        return response.json().get("content") or None
    except Exception as exc:  # noqa: BLE001 - the assistant must degrade, not 500
        logger.warning("RAG chat call failed: %s", exc)
        return None

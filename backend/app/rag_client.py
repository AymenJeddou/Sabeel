"""HTTP client for rag-service's POST /generate (real service boundary, not an import)."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from . import config

logger = logging.getLogger(__name__)


def generate(lat: float, lon: float, score: int, road_type: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Returns the RAG service's response dict, or None on any failure --
    callers must never let a RAG hiccup fail the whole POST /reports call."""
    payload = {"lat": lat, "lon": lon, "score": score}
    if road_type:
        payload["road_type"] = road_type

    try:
        response = httpx.post(
            f"{config.RAG_SERVICE_URL}/generate",
            json=payload,
            timeout=config.RAG_TIMEOUT_S,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001 - RAG failures must never surface as a 500 here
        logger.warning("RAG service call failed: %s", exc)
        return None

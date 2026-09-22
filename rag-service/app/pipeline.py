"""generate() -- the frozen WP2 -> WP3 interface (Section 4.4).

generate(lat, lon, score, road_type=None) -> {
    "sheet_text": str,
    "rule_citations": [{"rule_id", "source", "excerpt"}, ...],
    "target_office": str,
    "road_type": str,
    "generated_at": str,   # ISO 8601 UTC, trailing Z
    "generation_ms": float,
}

This function must never let an exception escape -- any failure routes to
the template fallback so a caller (e.g. the glue backend) never sees a 500
just because the LLM had a bad moment.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from . import config
from .citation_guard import validate_citations
from .generation import build_prompt, call_llm, pick_target_office, render_template_fallback
from .retrieval import retrieve_chunks
from .road_type import normalize_road_type

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _citations_from_chunks(chunks: list[dict]) -> list[dict]:
    return [
        {
            "rule_id": c["metadata"]["rule_id"],
            "source": c["metadata"]["source"],
            "excerpt": c["document"][:200],
        }
        for c in chunks
    ]


def generate(lat: float, lon: float, score: int, road_type: str | None = None) -> dict:
    start = time.perf_counter()

    try:
        resolved_road_type = normalize_road_type(road_type, lat, lon)
        shown_chunks = retrieve_chunks(resolved_road_type, score, top_k=config.TOP_K_RETRIEVE)
        shown_chunks = shown_chunks[: config.TOP_K_SHOWN]

        if not shown_chunks:
            sheet_text = render_template_fallback([], score, resolved_road_type, lat, lon, "Municipality")
            return _finalize(sheet_text, [], "Municipality", resolved_road_type, start)

        prompt = build_prompt(shown_chunks, score, resolved_road_type, lat, lon)
        llm_output = call_llm(prompt)

        target_office = pick_target_office(shown_chunks)

        if llm_output:
            validated_text, matched_chunks = validate_citations(llm_output, shown_chunks)
            if validated_text is not None:
                return _finalize(
                    validated_text,
                    _citations_from_chunks(matched_chunks),
                    target_office,
                    resolved_road_type,
                    start,
                )
            logger.info("LLM output failed citation validation; using template fallback.")

        sheet_text = render_template_fallback(shown_chunks, score, resolved_road_type, lat, lon, target_office)
        return _finalize(sheet_text, _citations_from_chunks(shown_chunks), target_office, resolved_road_type, start)

    except Exception:  # noqa: BLE001 - generate() must never raise
        logger.exception("generate() failed unexpectedly; returning safe fallback.")
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "sheet_text": (
                "Erreur interne lors de la génération de la fiche — "
                "vérification manuelle recommandée."
            ),
            "rule_citations": [],
            "target_office": "Municipality",
            "road_type": road_type or "rural",
            "generated_at": _now_iso(),
            "generation_ms": round(elapsed_ms, 2),
        }


def _finalize(sheet_text: str, citations: list[dict], target_office: str, road_type: str, start: float) -> dict:
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "sheet_text": sheet_text,
        "rule_citations": citations,
        "target_office": target_office,
        "road_type": road_type,
        "generated_at": _now_iso(),
        "generation_ms": round(elapsed_ms, 2),
    }

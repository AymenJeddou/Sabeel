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
from .generation import (
    OFFICE_LABELS_FR,
    LLMRateLimited,
    build_prompt,
    call_llm,
    pick_target_office,
    render_template_fallback,
)
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


def select_shown(chunks: list[dict], score: int, k: int) -> list[dict]:
    """Best chunks first, but always keep the best jurisdiction rule and the
    repair method that fits the severity (semi-permanent from 3, quick
    throw-and-roll below), so every sheet can say who and how."""
    if not chunks:
        return []
    want = [
        next((c for c in chunks if c["metadata"].get("target_office") in config.TARGET_OFFICES), None),
        next((c for c in chunks if c["metadata"]["rule_id"] == ("FHWA-99-168-S3.2.2" if score >= 3 else "FHWA-99-168-S3.2.1")), None),
    ]
    picked = [c for c in want if c]
    for c in chunks:
        if len(picked) >= k:
            break
        if c not in picked:
            picked.append(c)
    order = {id(c): i for i, c in enumerate(chunks)}
    return sorted(picked[:max(k, len([w for w in want if w]))], key=lambda c: order[id(c)])


def generate(
    lat: float, lon: float, score: int, road_type: str | None = None,
    office_name: str | None = None, address: str | None = None, jurisdiction: str | None = None,
) -> dict:
    start = time.perf_counter()

    try:
        resolved_road_type = normalize_road_type(road_type, lat, lon)
        shown_chunks = retrieve_chunks(resolved_road_type, score, top_k=config.TOP_K_RETRIEVE, jurisdiction=jurisdiction)
        shown_chunks = select_shown(shown_chunks, score, config.TOP_K_SHOWN)

        if not shown_chunks:
            sheet_text = render_template_fallback([], score, resolved_road_type, lat, lon, "Municipality", office_name)
            return _finalize(sheet_text, [], "Municipality", resolved_road_type, start)

        prompt = build_prompt(shown_chunks, score, resolved_road_type, lat, lon, office_name, address)
        retry_after = None
        try:
            llm_output = call_llm(prompt)
        except LLMRateLimited as exc:
            llm_output, retry_after = None, exc.retry_after_s

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
                    llm_used=True,
                )
            logger.info("LLM output failed citation validation; using template fallback.")

        sheet_text = render_template_fallback(shown_chunks, score, resolved_road_type, lat, lon, target_office, office_name)
        return _finalize(
            sheet_text, _citations_from_chunks(shown_chunks), target_office, resolved_road_type, start,
            retry_after_s=retry_after,
        )

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
            "target_office_label": OFFICE_LABELS_FR["Municipality"],
            "road_type": road_type or "rural",
            "generated_at": _now_iso(),
            "generation_ms": round(elapsed_ms, 2),
        }


def _finalize(
    sheet_text: str, citations: list[dict], target_office: str, road_type: str, start: float,
    llm_used: bool = False, retry_after_s: float | None = None,
) -> dict:
    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "sheet_text": sheet_text,
        "rule_citations": citations,
        "target_office": target_office,
        "target_office_label": OFFICE_LABELS_FR.get(target_office, target_office),
        "road_type": road_type,
        "generated_at": _now_iso(),
        "generation_ms": round(elapsed_ms, 2),
        # False = the rule-only template was used. retry_after_s set = the LLM
        # was rate-limited: the Core API retries later for a model-written sheet.
        "llm_used": llm_used,
        "retry_after_s": retry_after_s,
    }

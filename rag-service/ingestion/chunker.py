"""Chunking: one chunk = one article/clause (semantic, not fixed-window).

Only split a chunk further if it exceeds ~300 words, then into ~150-220 word
sub-chunks with ~30-40 word overlap. Hard cap of 1200 characters per chunk.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

MAX_CHARS = 1200
SPLIT_WORD_THRESHOLD = 300
SUB_CHUNK_WORDS = 200
OVERLAP_WORDS = 35


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _split_long_text(text: str) -> list[str]:
    words = text.split()
    if len(words) <= SPLIT_WORD_THRESHOLD:
        return [text[:MAX_CHARS]]

    parts = []
    start = 0
    while start < len(words):
        end = min(start + SUB_CHUNK_WORDS, len(words))
        parts.append(" ".join(words[start:end])[:MAX_CHARS])
        if end == len(words):
            break
        start = end - OVERLAP_WORDS
    return parts


def chunk_document(entries: list[dict[str, Any]], doc_meta: dict[str, Any]) -> list[dict[str, Any]]:
    """entries: list of raw rule dicts as loaded from a rules_*/*.yaml file, each
    already representing one article/clause (semantic unit chosen by the author,
    not derived automatically). Returns Chroma-ready {"id", "document", "metadata"}."""
    chunks = []
    for entry in entries:
        sub_texts = _split_long_text(entry["text"])
        for i, sub_text in enumerate(sub_texts):
            rule_id = entry["rule_id"] if len(sub_texts) == 1 else f"{entry['rule_id']}-{i+1}"
            metadata = {
                "rule_id": rule_id,
                "source": entry["source"],
                "road_type": entry["road_type"],
                "section": entry.get("section", ""),
                "lang": entry.get("lang", "fr"),
                "is_placeholder": bool(doc_meta.get("is_placeholder", True)),
                "severity_min": int(entry.get("severity_min", 3)),
                "target_office": entry["target_office"],
                # Who owns the road this rule is about: "municipal" | "state" | "any" (method rules).
                "jurisdiction": {"Municipality": "municipal", "any": "any"}.get(entry["target_office"], "state"),
                "doc_title": doc_meta.get("doc_title", ""),
                "ingested_at": _now_iso(),
            }
            chunks.append({"id": rule_id, "document": sub_text, "metadata": metadata})
    return chunks

"""Chroma-backed retrieval with an explicit similarity floor."""
from __future__ import annotations

from typing import Any

import chromadb

from . import config
from .embeddings import embed

_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def collection_count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0


def retrieve_chunks(road_type: str, score: int, top_k: int = None, jurisdiction: str | None = None) -> list[dict[str, Any]]:
    """Embed a synthetic query, search Chroma, apply the similarity floor.

    Returns a list of {"id", "document", "metadata", "similarity"} dicts,
    already filtered by config.MIN_SIMILARITY and sorted best-first.
    """
    top_k = top_k or config.TOP_K_RETRIEVE
    collection = get_collection()
    if collection.count() == 0:
        return []

    # The query names what a sheet needs at this severity: who owns the road,
    # the repair method, and (for dangerous ones) urgency and signage.
    method = (
        "réparation semi-permanente, découpe des bords, compactage" if score >= 3
        else "colmatage rapide à l'enrobé à froid, déposer et compacter"
    )
    urgency = ", urgence, signalisation et sécurité" if score >= 4 else ""
    query_text = f"nid de poule sévérité {score} route {road_type} : domaine routier responsable, {method}{urgency}"
    query_vec = embed([query_text])

    # Rules for this road type plus the general repair methods ("all"),
    # limited to rules that apply at this severity.
    results = collection.query(
        query_embeddings=query_vec,
        n_results=min(top_k, collection.count()),
        where={"$and": [
            {"road_type": {"$in": [road_type, "all"]}},
            {"severity_min": {"$lte": int(score)}},
            # When the Core API knows who owns the road (from OSM), only that
            # owner's legal rules (plus the method rules) are shown.
            {"jurisdiction": {"$in": [jurisdiction, "any"] if jurisdiction else ["municipal", "state", "any"]}},
        ]},
    )

    hits = _extract_hits(results)

    if len(hits) < 2:
        # Broaden: drop the filters, take the best 5 overall.
        results = collection.query(
            query_embeddings=query_vec,
            n_results=min(config.TOP_K_RETRIEVE, collection.count()),
        )
        hits = _extract_hits(results)

    surviving = [h for h in hits if h["similarity"] >= config.MIN_SIMILARITY]
    surviving.sort(key=lambda h: h["similarity"], reverse=True)
    return surviving


def _extract_hits(results: dict) -> list[dict[str, Any]]:
    hits = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]
    for id_, doc, meta, dist in zip(ids, docs, metas, dists):
        similarity = 1.0 - dist
        hits.append({"id": id_, "document": doc, "metadata": meta, "similarity": similarity})
    return hits

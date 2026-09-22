"""Lazy-singleton multilingual sentence embedder (free, local, CPU, handles French)."""
from __future__ import annotations

from typing import List

from sentence_transformers import SentenceTransformer

from . import config

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _model


def embed(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    vectors = get_model().encode(texts, normalize_embeddings=True)
    return vectors.tolist()

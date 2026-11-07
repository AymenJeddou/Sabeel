"""Idempotent CLI: rules_real/*.yaml -> chunks -> embeddings -> Chroma.

Usage:
    python -m ingestion.build_index

Wipes and rebuilds the road_rules_v1 collection from scratch every run, so it's
safe to re-run after editing any rule file.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.embeddings import embed  # noqa: E402
from app.retrieval import get_client  # noqa: E402
from ingestion.chunker import chunk_document  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RULE_DIRS = [(REPO_ROOT / "rules_real", False)]


def load_rule_files() -> list[dict]:
    all_chunks: list[dict] = []
    for directory, default_is_placeholder in RULE_DIRS:
        if not directory.exists():
            continue
        for yaml_path in sorted(directory.glob("*.yaml")):
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            doc_meta = {
                "doc_title": data.get("doc_title", yaml_path.stem),
                "is_placeholder": data.get("is_placeholder", default_is_placeholder),
            }
            entries = data.get("rules", [])
            chunks = chunk_document(entries, doc_meta)
            all_chunks.extend(chunks)
            print(f"  {yaml_path.relative_to(REPO_ROOT)}: {len(chunks)} chunk(s)")
    return all_chunks


def main() -> None:
    print("Loading rule files...")
    chunks = load_rule_files()
    print(f"Total chunks: {len(chunks)}")

    if not chunks:
        print("No rule files found -- nothing to index.")
        return

    print(f"Embedding {len(chunks)} chunk(s) with {config.EMBEDDING_MODEL_NAME}...")
    texts = [c["document"] for c in chunks]
    vectors = embed(texts)

    client = get_client()
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["document"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
        embeddings=vectors,
    )
    print(f"Indexed {collection.count()} chunk(s) into '{config.COLLECTION_NAME}' at {config.CHROMA_DB_PATH}")

    by_road_type: dict[str, int] = {}
    for c in chunks:
        rt = c["metadata"]["road_type"]
        by_road_type[rt] = by_road_type.get(rt, 0) + 1
    print("By road_type:", by_road_type)

    real_count = sum(1 for c in chunks if not c["metadata"]["is_placeholder"])
    print(f"Real (non-placeholder) chunks: {real_count}")


if __name__ == "__main__":
    main()

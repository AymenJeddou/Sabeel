"""Turns the human decisions stored by the Core API (feedback_labels) into a
YOLO dataset for retraining (issue #28, part B).

    DATABASE_URL=postgresql://... python export_feedback_dataset.py --photos ../backend/app/static
    python export_feedback_dataset.py --photos https://<project>.supabase.co   (remote photos)

Writes datasets/feedback_vN/ (N = next free number, never overwritten):
- images/ + labels/: `not_pothole` photos with an EMPTY label file (hard
  negatives: manholes, patches, shadows...); `confirmed_pothole` photos with
  the model's own boxes as pseudo-labels;
- manifest.csv: one row per image with its label, source (officer/citizen),
  model score and confidence, and `needs_review = yes` for every
  pseudo-labelled positive (a human must check the boxes before training);
- metrics.json: the false-positive rate (not_pothole / all labelled potholes).

Photos were already anonymised by the API (EXIF stripped, faces and plates
blurred). Merge with: python build_dataset.py --rdd ... --extra datasets/feedback_vN
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import urllib.request
from pathlib import Path

import asyncpg


async def fetch(dsn: str) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(dsn)
    try:
        return await conn.fetch(
            "SELECT id, label, source, photo_path, model_score, model_confidence, boxes, created_at "
            "FROM feedback_labels WHERE photo_path IS NOT NULL ORDER BY id"
        )
    finally:
        await conn.close()


def next_version(root: Path) -> Path:
    n = 1
    while (root / f"feedback_v{n}").exists():
        n += 1
    return root / f"feedback_v{n}"


def read_photo(photos: str, path: str) -> bytes | None:
    try:
        if path.startswith("http"):
            return urllib.request.urlopen(path, timeout=20).read()
        if photos.startswith("http"):
            return urllib.request.urlopen(photos.rstrip("/") + path, timeout=20).read()
        return (Path(photos) / path.removeprefix("/static/")).read_bytes()
    except Exception:  # noqa: BLE001 - a deleted photo is skipped, not fatal
        return None


def yolo_lines(boxes: list[dict] | None) -> list[str]:
    """API boxes are normalised x, y, w, h (top-left) -> YOLO cx cy w h."""
    out = []
    for b in boxes or []:
        out.append(f"0 {b['x'] + b['w'] / 2:.6f} {b['y'] + b['h'] / 2:.6f} {b['w']:.6f} {b['h']:.6f}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dsn", default=os.getenv("DATABASE_URL", "").replace("+asyncpg", ""))
    ap.add_argument("--photos", default="../backend/app/static", help="static folder or base URL of the photos")
    ap.add_argument("--root", type=Path, default=Path("datasets"))
    a = ap.parse_args()
    if not a.dsn:
        raise SystemExit("Set DATABASE_URL or pass --dsn")

    rows = asyncio.run(fetch(a.dsn))
    out = next_version(a.root)
    (out / "images").mkdir(parents=True)
    (out / "labels").mkdir(parents=True)
    manifest, written = [], {"not_pothole": 0, "confirmed_pothole": 0, "missing_photo": 0}
    for r in rows:
        data = read_photo(a.photos, r["photo_path"])
        if data is None:
            written["missing_photo"] += 1
            continue
        name = f"fb{r['id']:06d}"
        (out / "images" / f"{name}.jpg").write_bytes(data)
        boxes = json.loads(r["boxes"]) if isinstance(r["boxes"], str) else r["boxes"]
        lines = yolo_lines(boxes) if r["label"] == "confirmed_pothole" else []
        (out / "labels" / f"{name}.txt").write_text("\n".join(lines))
        written[r["label"]] += 1
        manifest.append({
            "image": f"{name}.jpg", "label": r["label"], "source": r["source"], "model_score": r["model_score"],
            "model_confidence": r["model_confidence"], "boxes": len(lines),
            "needs_review": "yes" if r["label"] == "confirmed_pothole" else "no",
            "created_at": r["created_at"].isoformat(),
        })

    with open(out / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0]) if manifest else ["image"])
        writer.writeheader()
        writer.writerows(manifest)
    labelled = written["not_pothole"] + written["confirmed_pothole"]
    metrics = {**written, "false_positive_rate": round(written["not_pothole"] / labelled, 3) if labelled else None}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(out, metrics)


if __name__ == "__main__":
    main()

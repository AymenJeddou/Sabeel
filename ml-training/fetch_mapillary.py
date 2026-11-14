"""Desk-only Tunisian test set (issue #44): real Tunisian street photos from
Mapillary, pre-labelled by the model, for a person to review at a computer.

    set MAPILLARY_TOKEN=MLY|...        (free: mapillary.com > Developers > Register an application)
    python fetch_mapillary.py --per-area 400 --out eval/tunisia_v1

Mapillary images are crowdsourced street-level photos under CC BY-SA 4.0
(attribution: the contributor's username, kept in MANIFEST.csv). Most are
taken from cars, so they look like the app's driving mode.

What it does, per area (Tunis, Ariana, Ben Arous, Sousse, Sfax, Bizerte, Nabeul,
Kairouan, Gabès):
1. pulls up to --per-area image ids in the area's bounding box (Graph API v4);
2. downloads the 1024 px version and runs the production model on it;
3. keeps every image where the model sees a pothole (candidate positives)
   AND an equal number of random images where it sees nothing (so potholes the
   model misses can still be found, and negatives are not cherry-picked);
4. writes images/, labels/ (the model's boxes as YOLO pre-labels, empty for the
   others) and MANIFEST.csv with the attribution and `needs_review = yes`.

Then a human reviews every image in Label Studio / Roboflow (import images +
YOLO labels): fix or delete wrong boxes, draw the missed potholes, keep the
negatives empty. Only then is it a test set: score it with
`python evaluate.py --data eval/tunisia_v1/data.yaml` and never train on it.
Faces and plates: Mapillary already blurs them; check during review anyway.
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import time
from pathlib import Path

import httpx

import inference

GRAPH = "https://graph.mapillary.com/images"
# (name, min_lon, min_lat, max_lon, max_lat): city centres and their main roads.
AREAS = [
    ("Tunis", 10.13, 36.78, 10.22, 36.84),
    ("Ariana", 10.15, 36.84, 10.22, 36.88),
    ("Ben Arous", 10.20, 36.72, 10.28, 36.77),
    ("Sousse", 10.58, 35.80, 10.65, 35.86),
    ("Sfax", 10.72, 34.71, 10.80, 34.77),
    ("Bizerte", 9.84, 37.25, 9.89, 37.29),
    ("Nabeul", 10.70, 36.44, 10.76, 36.47),
    ("Kairouan", 10.07, 35.66, 10.12, 35.70),
    ("Gabès", 10.07, 33.86, 10.12, 33.90),
]


def list_images(client: httpx.Client, token: str, bbox: tuple, limit: int) -> list[dict]:
    """Mapillary caps a bbox query; split the box into a 3x3 grid to spread the sample."""
    min_lon, min_lat, max_lon, max_lat = bbox
    out: dict[str, dict] = {}
    for i in range(3):
        for j in range(3):
            sub = (
                min_lon + (max_lon - min_lon) * i / 3, min_lat + (max_lat - min_lat) * j / 3,
                min_lon + (max_lon - min_lon) * (i + 1) / 3, min_lat + (max_lat - min_lat) * (j + 1) / 3,
            )
            r = client.get(GRAPH, params={
                "access_token": token,
                "bbox": ",".join(f"{v:.5f}" for v in sub),
                "fields": "id,thumb_1024_url,captured_at,creator,geometry",
                "limit": max(limit // 9, 10),
            })
            r.raise_for_status()
            for img in r.json().get("data", []):
                out[img["id"]] = img
            time.sleep(0.2)
    return list(out.values())[:limit]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--token", default=os.getenv("MAPILLARY_TOKEN", ""))
    ap.add_argument("--per-area", type=int, default=300, help="images scanned per area")
    ap.add_argument("--out", type=Path, default=Path("eval/tunisia_v1"))
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    if not a.token:
        raise SystemExit("Set MAPILLARY_TOKEN (free developer token from mapillary.com).")

    rng = random.Random(a.seed)
    (a.out / "images").mkdir(parents=True, exist_ok=True)
    (a.out / "labels").mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    with httpx.Client(timeout=30, headers={"User-Agent": "Sabeel eval set builder (student project)"}) as client:
        for name, *bbox in AREAS:
            images = list_images(client, a.token, tuple(bbox), a.per_area)
            positives, negatives = [], []
            for meta in images:
                url = meta.get("thumb_1024_url")
                if not url:
                    continue
                try:
                    data = client.get(url).content
                    result = inference.infer(data, source="driving_mode")
                except Exception:  # noqa: BLE001 - skip broken downloads
                    continue
                (positives if result["score"] is not None else negatives).append((meta, data, result))
            picked = positives + rng.sample(negatives, min(len(negatives), max(len(positives), 5)))
            for meta, data, result in picked:
                stem = f"mly_{meta['id']}"
                (a.out / "images" / f"{stem}.jpg").write_bytes(data)
                w, h = result["image_size"]
                lines = [
                    f"0 {(b['x'] + b['w'] / 2) / w:.6f} {(b['y'] + b['h'] / 2) / h:.6f} {b['w'] / w:.6f} {b['h'] / h:.6f}"
                    for b in result["boxes"]
                ]
                (a.out / "labels" / f"{stem}.txt").write_text("\n".join(lines))
                lon, lat = meta["geometry"]["coordinates"]
                rows.append({
                    "image": f"{stem}.jpg",
                    "source_person": (meta.get("creator") or {}).get("username", "unknown"),
                    "phone": "mapillary",
                    "city": name,
                    "date": str(meta.get("captured_at", "")),
                    "condition_tags": "model_positive" if result["score"] is not None else "model_negative",
                    "negative_type": "",
                    "licence": "CC BY-SA 4.0 (Mapillary)",
                    "mapillary_url": f"https://www.mapillary.com/app/?pKey={meta['id']}",
                    "lat": round(lat, 5),
                    "lon": round(lon, 5),
                    "needs_review": "yes",
                })
            print(f"{name}: scanned {len(images)}, model positives {len(positives)}, kept {len(picked)}")

    with open(a.out / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["image"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} images to review in {a.out} (labels are model pre-labels, not ground truth).")


if __name__ == "__main__":
    main()

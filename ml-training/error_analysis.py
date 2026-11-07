"""Error analysis on the VAL split (issue #46, step 1): exports the false
negatives and false positives at the production threshold, so 100 of each
can be tagged (small/far, water-filled, shadow, patch, cut off, label error)
before deciding between more data, higher resolution or a bigger model.

    python error_analysis.py --data datasets/sabeel_v2/data.yaml --out runs/errors

Writes runs/errors/{false_negatives,false_positives}/*.jpg with the boxes
drawn (green = label, amber = model), plus errors.csv with one row per image
and an empty `tag` column to fill in. IoU 0.5 decides whether a prediction
matches a label, like mAP50.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
import yaml

import inference


def iou(a: tuple, b: tuple) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    iw, ih = max(0, min(ax2, bx2) - max(ax1, bx1)), max(0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union else 0.0


def labels_xyxy(path: Path, w: int, h: int) -> list[tuple]:
    out = []
    if path.exists():
        for row in path.read_text().split("\n"):
            v = row.split()
            if len(v) == 5:
                cx, cy, bw, bh = (float(x) for x in v[1:])
                out.append(((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--split", default="val")
    ap.add_argument("--out", type=Path, default=Path("runs/errors"))
    ap.add_argument("--limit", type=int, default=100, help="max images exported per error type")
    a = ap.parse_args()
    if a.split == "test":
        raise SystemExit("Error analysis must not look at the test split.")

    cfg = yaml.safe_load(a.data.read_text())
    root = Path(cfg["path"])
    images_dir = root / cfg[a.split]
    labels_dir = images_dir.parent / "labels"
    for sub in ("false_negatives", "false_positives"):
        (a.out / sub).mkdir(parents=True, exist_ok=True)

    rows, counts = [], {"false_negatives": 0, "false_positives": 0}
    for img_path in sorted(images_dir.iterdir()):
        data = img_path.read_bytes()
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        truth = labels_xyxy(labels_dir / f"{img_path.stem}.txt", w, h)
        preds = [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]) for b in inference.infer(data)["boxes"]]
        missed = [t for t in truth if not any(iou(t, p) >= 0.5 for p in preds)]
        spurious = [p for p in preds if not any(iou(t, p) >= 0.5 for t in truth)]
        for kind, boxes in (("false_negatives", missed), ("false_positives", spurious)):
            if not boxes or counts[kind] >= a.limit:
                continue
            counts[kind] += 1
            canvas = img.copy()
            for t in truth:
                cv2.rectangle(canvas, (int(t[0]), int(t[1])), (int(t[2]), int(t[3])), (60, 180, 60), 3)
            for p in preds:
                cv2.rectangle(canvas, (int(p[0]), int(p[1])), (int(p[2]), int(p[3])), (23, 163, 232), 3)
            cv2.imwrite(str(a.out / kind / img_path.name), canvas)
            rel = [round((b[2] - b[0]) * (b[3] - b[1]) / (w * h), 4) for b in boxes]
            rows.append({"kind": kind, "image": img_path.name, "boxes": len(boxes), "rel_area": rel, "tag": ""})

    with open(a.out / "errors.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["kind", "image", "boxes", "rel_area", "tag"])
        writer.writeheader()
        writer.writerows(rows)
    print(counts, "->", a.out / "errors.csv")


if __name__ == "__main__":
    main()

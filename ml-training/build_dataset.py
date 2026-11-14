"""Builds the training dataset: RDD2022 D40 potholes + close-up pothole photos
+ pothole-free road photos, split 70 / 15 / 15 (issue #45).

    python build_dataset.py --rdd /path/to/RDD2022 --out datasets/sabeel_v2
    python build_dataset.py --rdd ... --closeup /path/to/closeup --neg-ratio 0.15 --seed 42

This is the single source of truth: the Colab notebook
(colab/train_pothole_yolo11s.ipynb, cell 4) calls this script. Same seed and
same steps as the notebook that produced models/pothole_model.onnx, so on the
same files the split is identical (compare the sorted test filenames with
the Drive cache `data_cache.zip` before trusting a rebuilt test set).

Sources:
- RDD2022 (figshare, CC BY-SA 4.0): Pascal VOC XML, only class D40 (pothole) kept;
  images without a D40 box are the pothole-free negatives.
- Close-ups: Hugging Face dataset Ryukijano/Pothole-detection-Yolov8 (Roboflow
  "Potholes Detection", CC BY 4.0), downloaded unless --closeup is given.
"""
from __future__ import annotations

import argparse
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

Item = tuple[Path, list[str]]


def rdd_items(root: Path) -> tuple[list[Item], list[Item]]:
    """(pothole images, pothole-free images) from the RDD2022 tree."""
    pos: list[Item] = []
    neg: list[Item] = []
    # Match each XML to its image by filename, wherever it sits in the tree.
    images = {p.stem: p for ext in ("jpg", "jpeg", "png") for p in root.rglob(f"*.{ext}")}
    xmls = list(root.rglob("*.xml"))
    print("XML files:", len(xmls), "| images:", len(images))
    for x in xmls:
        img = images.get(x.stem)
        if img is None:
            continue
        r = ET.parse(x).getroot()
        w, h = int(float(r.findtext("size/width") or 0)), int(float(r.findtext("size/height") or 0))
        if not w or not h:
            w, h = Image.open(img).size
        lines = []
        for o in r.iter("object"):
            if o.findtext("name", "").strip() != "D40":
                continue
            b = o.find("bndbox")
            x1, y1, x2, y2 = (float(b.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
            if x2 > x1 and y2 > y1:
                lines.append(f"0 {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
        (pos if lines else neg).append((img, lines))
    return pos, neg


def closeup_items(root: Path) -> list[Item]:
    """YOLO-format close-ups; polygons are converted to boxes."""
    out: list[Item] = []
    for split in ("train", "valid", "test"):
        for img in (root / split / "images").glob("*.jpg"):
            lbl = root / split / "labels" / f"{img.stem}.txt"
            lines = []
            if lbl.exists():
                for row in lbl.read_text().split("\n"):
                    v = [float(t) for t in row.split()[1:]]
                    if len(v) == 4:
                        cx, cy, bw, bh = v
                        if bw > 0 and bh > 0:
                            lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                    elif len(v) >= 6:
                        xs, ys = v[0::2], v[1::2]
                        x1, x2, y1, y2 = max(0, min(xs)), min(1, max(xs)), max(0, min(ys)), min(1, max(ys))
                        if x2 > x1 and y2 > y1:
                            lines.append(f"0 {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}")
            if lines:
                out.append((img, lines))
    return out


def split_and_write(pos: list[Item], neg: list[Item], out: Path, neg_ratio: float) -> dict[str, int]:
    """Mixes in negatives, shuffles, splits 70/15/15 and writes YOLO folders.
    Uses the module-level `random` state, seeded by the caller (as the notebook did)."""
    random.shuffle(neg)
    items = pos + neg[: int(len(pos) * neg_ratio)]
    random.shuffle(items)
    n = len(items)
    splits = {"train": items[: int(0.7 * n)], "val": items[int(0.7 * n): int(0.85 * n)], "test": items[int(0.85 * n):]}
    for split, rows in splits.items():
        (out / split / "images").mkdir(parents=True, exist_ok=True)
        (out / split / "labels").mkdir(parents=True, exist_ok=True)
        for i, (img, lines) in enumerate(rows):
            name = f"{i:06d}_{img.stem}"  # unique even if two sources share a filename
            shutil.copy(img, out / split / "images" / f"{name}{img.suffix}")
            (out / split / "labels" / f"{name}.txt").write_text("\n".join(lines))
    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: pothole\n"
    )
    return {k: len(v) for k, v in splits.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rdd", type=Path, required=True, help="unpacked RDD2022 folder")
    ap.add_argument("--closeup", type=Path, help="close-up set folder (default: download from Hugging Face)")
    ap.add_argument("--out", type=Path, default=Path("datasets/sabeel_v2"))
    ap.add_argument("--neg-ratio", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--extra", type=Path, action="append", default=[],
                    help="more YOLO-format folders (images/ + labels/), e.g. a feedback_vN export; repeatable")
    a = ap.parse_args()

    shutil.rmtree(a.out, ignore_errors=True)
    random.seed(a.seed)
    pos, neg = rdd_items(a.rdd)
    print("RDD2022 pothole images:", len(pos), "| pothole-free:", len(neg))
    if not pos:
        raise SystemExit("0 RDD2022 pothole images: check the --rdd folder")

    try:
        root = a.closeup
        if root is None:
            from huggingface_hub import snapshot_download

            root = Path(snapshot_download("Ryukijano/Pothole-detection-Yolov8", repo_type="dataset", local_dir="datasets/closeup"))
        close = closeup_items(root)
        pos += close
        print("close-up pothole images:", len(close))
    except Exception as e:  # noqa: BLE001 - optional source
        print("close-up pothole set skipped:", e)

    for extra in a.extra:
        for img in sorted((extra / "images").glob("*")):
            lbl = extra / "labels" / f"{img.stem}.txt"
            lines = [l for l in lbl.read_text().split("\n") if l.strip()] if lbl.exists() else []
            (pos if lines else neg).append((img, lines))
        print("extra folder:", extra)

    counts = split_and_write(pos, neg, a.out, a.neg_ratio)
    print("total pothole images:", len(pos), "|", counts)
    print("data.yaml:", a.out / "data.yaml")


if __name__ == "__main__":
    main()

"""Scores an ONNX model on a YOLO dataset split, with the production threshold.

    python evaluate.py --data datasets/sabeel_v2/data.yaml                      # test split, float model
    python evaluate.py --model models/pothole_model_int8.onnx --data ...        # issue #43
    python evaluate.py --data eval/tunisia_v1/data.yaml                          # issue #44

Two kinds of numbers:
1. mAP50, mAP50-95, precision, recall from ultralytics' validator at conf 0.001
   (the standard way, comparable with test_metrics.json);
2. what the API actually does (inference.infer at CONF_THRESHOLD = 0.28):
   pothole images found out of N, false alarms on pothole-free images out of M.

Never tune anything on the test split or on eval/tunisia_v1.
Needs `pip install -r requirements.txt` (ultralytics).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import yaml


def detection_rates(images: list[Path], labels_dir: Path) -> dict[str, int]:
    import inference

    found = missed = false_alarm = clean = 0
    for img in images:
        lbl = labels_dir / f"{img.stem}.txt"
        has_pothole = lbl.exists() and lbl.read_text().strip() != ""
        hit = inference.infer(img.read_bytes())["score"] is not None
        if has_pothole:
            found += hit
            missed += not hit
        else:
            false_alarm += hit
            clean += not hit
    return {"potholes_found": found, "potholes_total": found + missed, "false_alarms": false_alarm,
            "negatives_total": false_alarm + clean}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", type=Path, default=Path("models/pothole_model.onnx"))
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", type=Path, help="write the metrics as JSON here")
    a = ap.parse_args()
    os.environ["MODEL_PATH"] = str(a.model)

    cfg = yaml.safe_load(a.data.read_text())
    root = Path(cfg.get("path", a.data.parent))
    if not root.is_absolute():
        root = (a.data.parent / root).resolve()
    images_dir = root / cfg[a.split]
    labels_dir = images_dir.parent / "labels"
    images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))

    from ultralytics import YOLO

    m = YOLO(str(a.model), task="detect").val(data=str(a.data), split=a.split, imgsz=640, conf=0.001, plots=False)
    metrics = {
        "model": a.model.name,
        "data": str(a.data),
        "split": a.split,
        "images": len(images),
        "mAP50": round(float(m.box.map50), 4),
        "mAP50-95": round(float(m.box.map), 4),
        "precision": round(float(m.box.mp), 4),
        "recall": round(float(m.box.mr), 4),
        **detection_rates(images, labels_dir),
    }
    print(json.dumps(metrics, indent=2))
    if a.out:
        a.out.write_text(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

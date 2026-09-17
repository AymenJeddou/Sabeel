
"""
WP1 → WP3 Model Inference Interface (Section 4.3 of the Action Plan)

infer(image: bytes) -> {
    "score": int | None,
    "confidence": float | None,
    "boxes": [{"x": int, "y": int, "w": int, "h": int, "class": "pothole"}, ...],
    "inference_ms": float
}
"""

from __future__ import annotations
import time
import os
from typing import List, Dict, Any
from pathlib import Path
import numpy as np
import cv2
import onnxruntime as ort
from ultralytics import YOLO

from severity_scoring import score_from_detections

# Shared config (Section 4.6)
MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/pothole_model.onnx"))

# Load once
_session = None
_input_name = None
_output_names = None


def _get_session():
    global _session, _input_name, _output_names
    if _session is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"ONNX model not found at {MODEL_PATH}")
        providers = ["CPUExecutionProvider"]
        _session = ort.InferenceSession(str(MODEL_PATH), providers=providers)
        _input_name = _session.get_inputs()[0].name
        _output_names = [o.name for o in _session.get_outputs()]
    return _session, _input_name, _output_names


def _preprocess(image_bytes: bytes, imgsz: int = 640):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")

    orig_h, orig_w = img.shape[:2]
    img_resized = cv2.resize(img, (imgsz, imgsz))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_norm = img_rgb.astype(np.float32) / 255.0
    img_chw = np.transpose(img_norm, (2, 0, 1))[None, ...]  # 1x3xHxW
    return img_chw, (orig_h, orig_w)


def _postprocess(outputs, orig_shape, conf_thres=0.25, imgsz=640):
    """
    Simple post-processing for YOLOv8 ONNX output shape (1, 5, 8400)
    """
    pred = outputs[0]  # (1, 5, 8400)
    pred = np.squeeze(pred).T  # (8400, 5) → [x, y, w, h, conf]

    boxes = []
    orig_h, orig_w = orig_shape
    scale_x = orig_w / imgsz
    scale_y = orig_h / imgsz

    for row in pred:
        conf = float(row[4])
        if conf < conf_thres:
            continue

        # YOLO format is center_x, center_y, width, height (normalized to 640)
        cx, cy, w, h = row[:4]
        x1 = int((cx - w / 2) * scale_x)
        y1 = int((cy - h / 2) * scale_y)
        bw = int(w * scale_x)
        bh = int(h * scale_y)

        # Clamp to image
        x1 = max(0, x1)
        y1 = max(0, y1)
        bw = min(bw, orig_w - x1)
        bh = min(bh, orig_h - y1)

        if bw > 5 and bh > 5:  # ignore tiny boxes
            boxes.append({
                "x": x1,
                "y": y1,
                "w": bw,
                "h": bh,
                "conf": conf,
                "class": "pothole"
            })

    # Simple NMS (very basic – good enough for Sprint 1)
    boxes = sorted(boxes, key=lambda b: b["conf"], reverse=True)
    keep = []
    while boxes:
        best = boxes.pop(0)
        keep.append(best)
        boxes = [
            b for b in boxes
            if not (
                abs(b["x"] - best["x"]) < best["w"] * 0.5 and
                abs(b["y"] - best["y"]) < best["h"] * 0.5
            )
        ]
    return keep


def infer(image: bytes) -> Dict[str, Any]:
    """
    Exact interface required by Section 4.3 of the Action Plan.
    """
    t0 = time.perf_counter()

    session, input_name, _ = _get_session()
    input_tensor, (orig_h, orig_w) = _preprocess(image)

    outputs = session.run(None, {input_name: input_tensor})
    boxes = _postprocess(outputs, (orig_h, orig_w))

    confidences = [b["conf"] for b in boxes]
    overall_conf = float(max(confidences)) if confidences else 0.0

    score = score_from_detections(boxes, orig_w, orig_h)

    inference_ms = (time.perf_counter() - t0) * 1000.0

    # Clean boxes for the contract (no conf field)
    clean_boxes = [
        {"x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"], "class": "pothole"}
        for b in boxes
    ]

    return {
        "score": score if score > 0 else None,
        "confidence": overall_conf if overall_conf > 0 else None,
        "boxes": clean_boxes,
        "inference_ms": round(inference_ms, 2),
    }


# Quick self-test
if __name__ == "__main__":
    # Put any pothole image path here for a quick test
    test_img = Path("datasets/yolo_annotated_potholes/images/val")
    imgs = list(test_img.glob("*.jpg")) + list(test_img.glob("*.png"))
    if imgs:
        with open(imgs[0], "rb") as f:
            result = infer(f.read())
        print("Self-test result:")
        print(result)
    else:
        print("No test image found – place one and re-run.")
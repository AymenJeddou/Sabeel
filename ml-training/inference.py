
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

from severity_scoring import score_from_detections

# Shared config (Section 4.6)
MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/pothole_model.onnx"))
# 0 lets ONNX Runtime pick (all physical cores); set it to the server's vCPU count on Cloud Run.
INTRA_OP_THREADS = int(os.getenv("ONNX_INTRA_OP_THREADS", "0"))
# Tuned on the validation split (max F1), see ml-training/README.md
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.28"))
NMS_IOU = 0.45

# Load once
_session = None
_input_name = None
_imgsz = None


def _get_session():
    global _session, _input_name, _imgsz
    if _session is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"ONNX model not found at {MODEL_PATH}")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = INTRA_OP_THREADS
        _session = ort.InferenceSession(str(MODEL_PATH), sess_options=opts, providers=["CPUExecutionProvider"])
        inp = _session.get_inputs()[0]
        _input_name = inp.name
        _imgsz = int(inp.shape[2])  # fixed square input baked into the export (640, 800, ...)
    return _session, _input_name, _imgsz


def _preprocess(image_bytes: bytes, imgsz: int):
    """Letterbox like Ultralytics training: keep aspect ratio, pad with grey (114)."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")

    orig_h, orig_w = img.shape[:2]
    r = min(imgsz / orig_h, imgsz / orig_w)
    new_w, new_h = round(orig_w * r), round(orig_h * r)
    pad_x, pad_y = (imgsz - new_w) / 2, (imgsz - new_h) / 2
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    top, left = round(pad_y - 0.1), round(pad_x - 0.1)
    canvas = cv2.copyMakeBorder(resized, top, imgsz - new_h - top, left, imgsz - new_w - left,
                                cv2.BORDER_CONSTANT, value=(114, 114, 114))

    img_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    img_chw = np.transpose(img_rgb.astype(np.float32) / 255.0, (2, 0, 1))[None, ...]  # 1x3xHxW
    return img_chw, (orig_h, orig_w), r, (left, top)


def _postprocess(outputs, orig_shape, ratio, pad, conf_thres=CONF_THRESHOLD):
    """YOLOv8/YOLO11 single-class output (1, 5, N): rows of [cx, cy, w, h, conf] in letterbox pixels."""
    pred = np.squeeze(outputs[0]).T  # (N, 5)
    pred = pred[pred[:, 4] >= conf_thres]
    if not len(pred):
        return []

    orig_h, orig_w = orig_shape
    left, top = pad
    cx, cy, w, h, conf = pred.T
    x1 = np.clip((cx - w / 2 - left) / ratio, 0, orig_w)
    y1 = np.clip((cy - h / 2 - top) / ratio, 0, orig_h)
    x2 = np.clip((cx + w / 2 - left) / ratio, 0, orig_w)
    y2 = np.clip((cy + h / 2 - top) / ratio, 0, orig_h)

    xywh = np.stack([x1, y1, x2 - x1, y2 - y1], axis=1)
    keep = cv2.dnn.NMSBoxes(xywh.tolist(), conf.tolist(), conf_thres, NMS_IOU)
    boxes = []
    for i in np.array(keep).flatten():
        bx, by, bw, bh = (int(v) for v in xywh[i])
        if bw > 5 and bh > 5:  # ignore tiny boxes
            boxes.append({"x": bx, "y": by, "w": bw, "h": bh, "conf": float(conf[i]), "class": "pothole"})
    return sorted(boxes, key=lambda b: b["conf"], reverse=True)


def warm_up() -> None:
    """Loads the ONNX session (~0.5 s) so the first real request doesn't pay for it."""
    _get_session()


def infer(image: bytes, source: str = "manual") -> Dict[str, Any]:
    """
    Interface of Section 4.3 of the Action Plan. `source` (manual | web |
    driving_mode) selects the severity bands, see severity_scoring.py.
    """
    t0 = time.perf_counter()

    session, input_name, imgsz = _get_session()
    input_tensor, (orig_h, orig_w), ratio, pad = _preprocess(image, imgsz)

    outputs = session.run(None, {input_name: input_tensor})
    boxes = _postprocess(outputs, (orig_h, orig_w), ratio, pad)

    confidences = [b["conf"] for b in boxes]
    overall_conf = float(max(confidences)) if confidences else 0.0

    score = score_from_detections(boxes, orig_w, orig_h, conf_threshold=CONF_THRESHOLD, source=source)

    inference_ms = (time.perf_counter() - t0) * 1000.0

    # Boxes keep their confidence: the dashboard draws them over the photo.
    clean_boxes = [
        {"x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"], "conf": round(b["conf"], 3), "class": "pothole"}
        for b in boxes
    ]

    return {
        "score": score if score > 0 else None,
        "confidence": overall_conf if overall_conf > 0 else None,
        "boxes": clean_boxes,
        "image_size": [orig_w, orig_h],
        "inference_ms": round(inference_ms, 2),
    }


# Quick self-test
if __name__ == "__main__":
    import sys
    test_img = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../backend/app/static/photos/_seed/p01.jpg")
    if test_img.exists():
        result = infer(test_img.read_bytes())
        print("Self-test result:")
        print(result)
    else:
        print("No test image found – pass an image path.")

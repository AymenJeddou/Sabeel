"""Wraps ml-training/inference.py::infer() for in-process use by the Core API.

infer() is a plain importable function (Section 4.3), not an HTTP service.
inference.py does a same-directory `from severity_scoring import ...`, so
ml-training/ itself (not its parent) must be on sys.path.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ML_TRAINING_DIR = REPO_ROOT / "ml-training"

if str(ML_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(ML_TRAINING_DIR))

os.environ.setdefault("MODEL_PATH", str(ML_TRAINING_DIR / "models" / "pothole_model.onnx"))

import inference as _vision_inference  # noqa: E402


def warm_up() -> None:
    _vision_inference.warm_up()


def run_inference(photo_bytes: bytes, source: str = "manual") -> dict[str, Any]:
    """{"score", "confidence", "boxes", "inference_ms"}; score/confidence are
    None when nothing is detected. Boxes are normalised to 0-1 of the image so
    they can be drawn over the (downscaled, anonymised) stored photo."""
    result = _vision_inference.infer(photo_bytes, source=source)
    w, h = result.pop("image_size", (1, 1))
    result["boxes"] = [
        {"x": b["x"] / w, "y": b["y"] / h, "w": b["w"] / w, "h": b["h"] / h, "conf": b.get("conf")}
        for b in result["boxes"]
    ]
    return result


async def run_inference_async(photo_bytes: bytes, source: str = "manual") -> dict[str, Any]:
    """Same, off the event loop (~240 ms of CPU per photo)."""
    try:
        return await asyncio.to_thread(run_inference, photo_bytes, source)
    except Exception:  # noqa: BLE001 - an undecodable photo is "no detection", not a 500
        return {"score": None, "confidence": None, "boxes": [], "inference_ms": None}

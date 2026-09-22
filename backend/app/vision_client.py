"""Wraps ml-training/inference.py::infer() for in-process use by the Core API.

infer() is a plain importable function (Section 4.3), not an HTTP service.
inference.py does a same-directory `from severity_scoring import ...`, so
ml-training/ itself (not its parent) must be on sys.path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ML_TRAINING_DIR = REPO_ROOT / "ml-training"

if str(ML_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(ML_TRAINING_DIR))

os.environ.setdefault("MODEL_PATH", str(ML_TRAINING_DIR / "models" / "pothole_model.onnx"))

import inference as _vision_inference  # noqa: E402


def run_inference(photo_bytes: bytes) -> dict[str, Any]:
    """Returns {"score": Optional[int], "confidence": Optional[float], "boxes": [...], "inference_ms": float}.

    score/confidence are None when nothing is detected -- callers must treat
    them as Optional, never assume a plain int/float (Section 4.3 documents
    plain int/float, but the actual implementation returns None on no
    detection; this has been true since Sprint 1).
    """
    return _vision_inference.infer(photo_bytes)


def meets_sheet_threshold(score: Optional[int], threshold: int) -> bool:
    return score is not None and score >= threshold

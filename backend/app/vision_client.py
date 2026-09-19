"""Wraps ml-training/inference.py::infer() for in-process use by the glue backend.

infer() is a plain importable function (per Section 4.3), not an HTTP service.
inference.py does a same-directory `from severity_scoring import ...`, so
ml-training/ itself (not its parent) must be on sys.path.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Optional

from . import config

if str(config.ML_TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(config.ML_TRAINING_DIR))

os.environ.setdefault("MODEL_PATH", str(config.MODEL_PATH))

import inference as _vision_inference  # noqa: E402


def run_inference(photo_bytes: bytes) -> dict[str, Any]:
    """Returns {"score": Optional[int], "confidence": Optional[float], "boxes": [...], "inference_ms": float}.

    score/confidence are None when nothing is detected -- callers must treat
    them as Optional, never assume a plain int/float (see Sprint 1 plan §2).
    """
    return _vision_inference.infer(photo_bytes)


def meets_sheet_threshold(score: Optional[int]) -> bool:
    return score is not None and score >= config.SCORE_THRESHOLD_FOR_SHEET

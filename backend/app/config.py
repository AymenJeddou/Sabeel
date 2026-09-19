"""Shared config for the glue backend (Section 4.6 of docs/Sprint1_Action_Plan.md).

TEMPORARY INSURANCE GLUE -- see backend/app/README.md and GitHub issue #4.
Homed here (not rag-service/) so Jasseur/Tharaa's real WP3 work can replace
these files in place once it lands.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

ML_TRAINING_DIR = REPO_ROOT / "ml-training"
MODEL_PATH = ML_TRAINING_DIR / "models" / "pothole_model.onnx"

REPORTS_DB_PATH = os.getenv("REPORTS_DB_PATH", str(Path(__file__).resolve().parent / "reports.db"))
STATIC_PHOTOS_DIR = Path(__file__).resolve().parent / "static" / "photos"

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")
RAG_TIMEOUT_S = float(os.getenv("RAG_TIMEOUT_S", "15"))

MAX_DEDUP_DISTANCE_M = float(os.getenv("MAX_DEDUP_DISTANCE_M", "5"))
SCORE_THRESHOLD_FOR_SHEET = int(os.getenv("SCORE_THRESHOLD_FOR_SHEET", "3"))

PORT = int(os.getenv("PORT", "8000"))

STATUS_ORDER = ["new", "confirmed", "sheet_sent", "fixed"]

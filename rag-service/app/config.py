"""Shared config for the RAG service (Section 4.6 of docs/Sprint1_Action_Plan.md)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
HF_MODEL_PRIMARY = os.getenv("HF_MODEL_PRIMARY", "Qwen/Qwen2.5-7B-Instruct")
HF_MODEL_BACKUP = os.getenv("HF_MODEL_BACKUP", "meta-llama/Llama-3.2-3B-Instruct")

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = "road_rules_v1"

MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.35"))
TOP_K_RETRIEVE = int(os.getenv("TOP_K_RETRIEVE", "5"))
TOP_K_SHOWN = int(os.getenv("TOP_K_SHOWN", "3"))
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "12"))

PORT = int(os.getenv("PORT", "8001"))

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

ROAD_TYPES = ["urbain_principal", "urbain_secondaire", "rural", "autoroute", "piste"]
TARGET_OFFICES = ["Municipality", "DGPC", "Ministry of Equipment"]

SCORE_THRESHOLD_FOR_SHEET = int(os.getenv("SCORE_THRESHOLD_FOR_SHEET", "3"))

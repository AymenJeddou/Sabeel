"""Pydantic models matching the frozen contract in docs/Sprint1_Action_Plan.md Section 4.4."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    lat: float
    lon: float
    score: int = Field(ge=1, le=5)
    road_type: Optional[str] = None


class RuleCitation(BaseModel):
    rule_id: str
    source: str
    excerpt: str


class GenerateResponse(BaseModel):
    sheet_text: str
    rule_citations: list[RuleCitation]
    target_office: str
    road_type: str
    generated_at: str
    generation_ms: float


class HealthResponse(BaseModel):
    status: str
    chunks_indexed: int

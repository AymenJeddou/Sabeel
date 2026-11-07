"""Pydantic models matching the frozen contract in docs/Sprint1_Action_Plan.md Section 4.4."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    lat: float
    lon: float
    score: int = Field(ge=1, le=5)
    road_type: Optional[str] = None
    # Additive (Sprint 3): the office the Core API routed the pothole to and its
    # address, so the sheet names the real recipient.
    office_name: Optional[str] = Field(default=None, max_length=200)
    address: Optional[str] = Field(default=None, max_length=300)
    jurisdiction: Optional[str] = Field(default=None, pattern="^(municipal|state)$")


class RuleCitation(BaseModel):
    rule_id: str
    source: str
    excerpt: str


class GenerateResponse(BaseModel):
    sheet_text: str
    rule_citations: list[RuleCitation]
    target_office: str
    target_office_label: str = ""  # French label for the UI (issue #11)
    road_type: str
    generated_at: str
    generation_ms: float
    llm_used: bool = False
    retry_after_s: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    chunks_indexed: int

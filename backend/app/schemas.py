"""Pydantic response models -- shapes match Section 4.5 exactly (plus documented additions)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ReportCreatedResponse(BaseModel):
    report_id: str
    device_report_id: str
    status: str
    score: Optional[int] = None
    # Additive fields beyond Section 4.5's illustrative shape -- populated
    # only when the synchronous RAG call succeeds this request. Not a shape
    # violation: field names/types elsewhere are unchanged, this is extra
    # information a real async WP3 implementation wouldn't have yet.
    sheet_summary: Optional[str] = None
    target_office: Optional[str] = None


class MapPoint(BaseModel):
    report_id: str
    lat: float
    lon: float
    score: Optional[int] = None
    status: str
    cluster_id: Optional[str] = None


class ReportStatusResponse(BaseModel):
    report_id: str
    status: str
    score: Optional[int] = None
    sheet_summary: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str


class StatusUpdateResponse(BaseModel):
    report_id: str
    status: str
    updated_at: str

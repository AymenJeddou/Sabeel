"""Pydantic response models -- shapes match Section 4.5 exactly (plus documented additions)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ReportCreatedResponse(BaseModel):
    report_id: str
    device_report_id: str
    status: str
    score: Optional[int] = None


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

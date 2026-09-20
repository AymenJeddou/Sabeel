"""
Pydantic request/response models mirroring Sprint1_Action_Plan.md Sections 4.1 and 4.5
field-for-field. Do not rename fields (lat/lon, never lng — see Section 5 of the plan).
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.status import ReportStatus


class ReportSource(str, Enum):
    MANUAL = "manual"
    DRIVING_MODE = "driving_mode"


class ReportCreateResponse(BaseModel):
    report_id: UUID
    device_report_id: str
    status: ReportStatus
    score: int | None = None


class MapReport(BaseModel):
    report_id: UUID
    lat: float
    lon: float
    score: int | None
    status: ReportStatus
    cluster_id: UUID | None


class ReportDetail(BaseModel):
    report_id: UUID
    status: ReportStatus
    score: int | None
    sheet_summary: str | None = None


class StatusUpdateRequest(BaseModel):
    status: ReportStatus


class StatusUpdateResponse(BaseModel):
    report_id: UUID
    status: ReportStatus
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Transition is not forward"])

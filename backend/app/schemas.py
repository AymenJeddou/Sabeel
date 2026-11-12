"""Pydantic request/response models.

Field names follow the frozen contracts (lat/lon, never lng; UTC timestamps).
Public models are explicit allow-lists: anything not declared here can never
leak into a citizen-facing or public response (device ids, photos of others,
sheet text). `tests/test_public.py` enforces that.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from backend.app.status import ReportStatus


class ReportSource(str, Enum):
    MANUAL = "manual"
    DRIVING_MODE = "driving_mode"
    WEB = "web"


SheetStatus = Literal["queued", "generated", "approved", "failed"]
ConfirmationKind = Literal["seen", "fixed_ok", "not_fixed", "not_pothole"]


# --- Citizen side -----------------------------------------------------------

class ReportCreateResponse(BaseModel):
    report_id: UUID
    device_report_id: str
    pothole_id: UUID | None
    ref: str | None
    detected: bool
    needs_review: bool
    status: ReportStatus
    score: int | None = None
    confidence: float | None = None
    sheet_status: SheetStatus | None = None
    # Kept for Sprint 1 clients. Sheets are generated in the background now,
    # so these are always null at creation time; poll the report instead.
    sheet_summary: str | None = None
    target_office: str | None = None


class TimelineStep(BaseModel):
    status: str
    at: datetime


class ReportDetail(BaseModel):
    """GET /reports/{device_report_id}: what the phone that sent it may see."""

    report_id: UUID
    device_report_id: str
    pothole_id: UUID | None
    ref: str | None
    status: ReportStatus
    score: int | None
    severity: int | None
    detected: bool
    sheet_status: SheetStatus | None
    sheet_summary: str | None = None  # first lines of the approved sheet only
    target_office: str | None
    address_label: str | None
    photo_url: str | None
    created_at: datetime
    updated_at: datetime
    fixed_at: datetime | None
    timeline: list[TimelineStep]


class DeviceReport(BaseModel):
    device_report_id: str
    report_id: UUID
    pothole_id: UUID | None
    ref: str | None
    status: ReportStatus
    score: int | None
    severity: int | None
    detected: bool
    sheet_status: SheetStatus | None
    target_office: str | None
    address_label: str | None
    photo_url: str | None
    lat: float
    lon: float
    created_at: datetime
    updated_at: datetime
    fixed_at: datetime | None


class ConfirmationIn(BaseModel):
    device_id: str = Field(min_length=8, max_length=100)
    kind: ConfirmationKind
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    gps_accuracy_m: float = Field(ge=0, le=10000)


class ConfirmationOut(BaseModel):
    pothole_id: UUID
    kind: ConfirmationKind
    created: bool
    status: ReportStatus
    confirm_count: int
    device_count: int
    fixed_ok_count: int
    not_fixed_count: int
    not_pothole_count: int


class Detection(BaseModel):
    """POST /detect (driving mode): a frame is scored, never stored."""

    detected: bool
    score: int | None
    confidence: float | None
    boxes: list[dict[str, Any]]
    inference_ms: float | None


# --- Public (map, transparency page) ---------------------------------------

class MapItem(BaseModel):
    pothole_id: UUID
    ref: str
    lat: float
    lon: float
    score: int | None
    status: ReportStatus
    report_count: int
    confirm_count: int
    address_label: str | None
    created_on: date
    # Sprint 1 compatibility: one map row is now one pothole.
    report_id: UUID | None = None
    cluster_id: UUID | None = None


class PublicPothole(BaseModel):
    pothole_id: UUID
    ref: str
    lat: float
    lon: float
    status: ReportStatus
    severity: int | None
    report_count: int
    device_count: int
    confirm_count: int
    fixed_ok_count: int
    not_fixed_count: int
    road_name: str | None
    address_label: str | None
    municipality: str | None
    region: str | None
    target_office: str | None
    sheet_status: SheetStatus | None
    sla_level: str | None
    fix_verified: bool
    created_on: date
    confirmed_on: date | None
    fixed_on: date | None


class PublicMapPoint(BaseModel):
    lat: float
    lon: float
    severity: int | None
    status: ReportStatus


class SheetVerification(BaseModel):
    pothole_id: UUID
    ref: str
    valid: bool
    approved_on: date | None
    office: str | None


# --- Officer side -----------------------------------------------------------

class StatusUpdateRequest(BaseModel):
    status: ReportStatus
    note: str | None = Field(default=None, max_length=1000)


class StatusUpdateResponse(BaseModel):
    report_id: UUID | None = None
    pothole_id: UUID | None = None
    status: ReportStatus
    updated_at: datetime


class SheetEdit(BaseModel):
    sheet_text: str = Field(min_length=10, max_length=8000)


class FeedbackIn(BaseModel):
    label: Literal["not_pothole", "confirmed_pothole"]
    note: str | None = Field(default=None, max_length=1000)


class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Transition is not forward"])


# --- Messages and assistant -------------------------------------------------

class MessageIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    sender: Literal["citizen", "authority"]
    body: str = Field(min_length=1, max_length=2000)


class MessageOut(MessageIn):
    message_id: UUID
    created_at: datetime


class Conversation(BaseModel):
    device_id: str
    last_body: str
    last_sender: str
    last_at: datetime
    count: int
    reports: int


class AssistantTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    # Only the last 6 turns reach the prompt; a longer list is refused instead of parsed.
    history: list[AssistantTurn] = Field(default_factory=list, max_length=20)


class AssistantReply(BaseModel):
    answer: str
    refs: list[dict[str, Any]]
    source: Literal["llm", "fallback"]

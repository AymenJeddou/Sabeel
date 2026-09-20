"""
POST /reports, GET /reports/{device_report_id}, PATCH /reports/{report_id}
Sprint 1: stub data per Sprint1_Action_Plan.md Section 4.5. PATCH is wired to the
real state-machine validity check (Section 4.2) against an in-memory fake "current
status" — everything else is hard-coded until Sprint 2 wires up the database.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status as http_status

from backend.app.schemas import (
    ReportCreateResponse,
    ReportDetail,
    ReportSource,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from backend.app.status import ReportStatus, is_valid_transition

router = APIRouter(tags=["reports"])

# Sprint 1 stand-in for the `reports` table — every report PATCHed in this process
# is treated as currently "confirmed", just to exercise the transition check end to end.
_FAKE_CURRENT_STATUS = ReportStatus.CONFIRMED


@router.post("/reports", response_model=ReportCreateResponse, status_code=http_status.HTTP_201_CREATED)
async def create_report(
    device_report_id: str = Form(...),
    photo: UploadFile = File(...),
    lat: float = Form(...),
    lon: float = Form(...),
    gps_accuracy_m: float = Form(...),
    speed_kmh: float = Form(...),
    direction_deg: float = Form(...),
    captured_at: datetime = Form(...),
    source: ReportSource = Form(...),
) -> ReportCreateResponse:
    return ReportCreateResponse(
        report_id=uuid.uuid4(),
        device_report_id=device_report_id,
        status=ReportStatus.NEW,
        score=None,
    )


@router.get("/reports/{device_report_id}", response_model=ReportDetail)
async def get_report(device_report_id: str) -> ReportDetail:
    return ReportDetail(
        report_id=uuid.uuid4(),
        status=ReportStatus.CONFIRMED,
        score=4,
        sheet_summary=None,
    )


@router.patch("/reports/{report_id}", response_model=StatusUpdateResponse)
async def update_report_status(report_id: uuid.UUID, body: StatusUpdateRequest) -> StatusUpdateResponse:
    if not is_valid_transition(_FAKE_CURRENT_STATUS, body.status):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Transition from '{_FAKE_CURRENT_STATUS.value}' to '{body.status.value}' is not forward",
        )
    return StatusUpdateResponse(
        report_id=report_id,
        status=body.status,
        updated_at=datetime.now(timezone.utc),
    )

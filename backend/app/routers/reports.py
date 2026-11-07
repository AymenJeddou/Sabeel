"""Citizen reports: POST /reports, GET /reports/{device_report_id},
GET /devices/{device_id}/reports, POST /detect (driving mode).

POST /reports pipeline (target < 3 s, no LLM in the request path):
validate -> run the vision model on the original photo -> detection gate ->
anonymise (EXIF strip, face/plate blur) -> store -> attach to a pothole within
5 m (PostGIS) -> distinct-device confirmation -> enqueue enrichment / sheet
jobs, which run in the background.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi import status as http
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import jobs, privacy, storage
from backend.app.auth import ensure_scope, require_office
from backend.app.config import settings
from backend.app.db import get_db
from backend.app.db_models import Office, Pothole, Report
from backend.app.potholes import InvalidTransition, assign_report, set_status
from backend.app.ratelimit import limit
from backend.app.schemas import (
    Detection,
    DeviceReport,
    ReportCreateResponse,
    ReportDetail,
    ReportSource,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from backend.app.serialize import device_report, office_map, office_name, sheet_summary, timeline
from backend.app.vision_client import run_inference_async

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reports"])

# Kept for the seed script and tests.
STATIC_PHOTOS_DIR = storage.PHOTOS_DIR


async def read_photo(photo: UploadFile) -> bytes:
    """Reads at most MAX_UPLOAD_MB and checks the magic bytes (JPEG or PNG)."""
    max_bytes = int(settings.max_upload_mb * 1024 * 1024)
    data = await photo.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(http.HTTP_413_CONTENT_TOO_LARGE, f"Photo larger than {settings.max_upload_mb:g} MB")
    if privacy.sniff_image_type(data) is None:
        raise HTTPException(http.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Photo must be a JPEG or PNG image")
    return data


def _validate(lat: float, lon: float, captured_at: datetime, direction_deg: float | None) -> None:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "lat/lon out of range")
    if direction_deg is not None and not 0 <= direction_deg <= 360:
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "direction_deg must be within 0-360")
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if captured_at > now + timedelta(minutes=5):
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "captured_at is in the future")
    if captured_at < now - timedelta(days=settings.max_report_age_days):
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "captured_at is too old")


async def _create_response(db: AsyncSession, r: Report) -> dict:
    p = await db.get(Pothole, r.pothole_id) if r.pothole_id else None
    offices = await office_map(db) if p else {}
    return {
        "report_id": r.report_id,
        "device_report_id": r.device_report_id,
        "pothole_id": r.pothole_id,
        "ref": p.ref if p else None,
        "detected": r.detected,
        "needs_review": r.needs_review if p is None else p.needs_review,
        "status": p.status if p else r.status,
        "score": r.score,
        "confidence": r.confidence,
        "sheet_status": p.sheet_status if p else None,
        "sheet_summary": sheet_summary(p),
        "target_office": office_name(offices, p.target_office_id) if p else None,
    }


@router.post(
    "/reports",
    response_model=ReportCreateResponse,
    status_code=http.HTTP_201_CREATED,
    responses={200: {"description": "Same device_report_id sent again: the existing report"}},
    dependencies=[Depends(limit("reports_device", 10, 60, by="device")), Depends(limit("reports_ip", 60, 3600))],
)
async def create_report(
    response: Response,
    background: BackgroundTasks,
    device_report_id: str = Form(..., min_length=8, max_length=100),
    photo: UploadFile = File(...),
    lat: float = Form(...),
    lon: float = Form(...),
    captured_at: datetime = Form(...),
    source: ReportSource = Form(...),
    device_id: str | None = Form(None, max_length=100),
    gps_accuracy_m: float | None = Form(None),
    speed_kmh: float = Form(0),
    direction_deg: float | None = Form(None),  # optional: browsers often have no compass
    force: bool = Form(False),  # "Send anyway" after a no-detection answer
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await db.scalar(select(Report).where(Report.device_report_id == device_report_id))
    if existing is not None:
        # Idempotent retry. The only change a retry may bring is force=true.
        if force and existing.pothole_id is None:
            await assign_report(db, existing)
            await db.commit()
            background.add_task(jobs.kick)
        response.status_code = http.HTTP_200_OK
        return await _create_response(db, existing)

    _validate(lat, lon, captured_at, direction_deg)
    raw = await read_photo(photo)
    result = await run_inference_async(raw, source.value)
    score, confidence = result.get("score"), result.get("confidence")
    detected = score is not None and (confidence or 0) >= settings.min_confidence

    try:
        clean, blurred = privacy.anonymize(raw, blur=settings.blur_faces_and_plates)
    except ValueError as exc:
        raise HTTPException(http.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Photo could not be decoded") from exc
    report_id = uuid.uuid4()
    photo_url = await storage.save(f"{report_id}.jpg", clean)

    report = Report(
        report_id=report_id,
        device_report_id=device_report_id,
        photo_url=photo_url,
        lat=lat,
        lon=lon,
        gps_accuracy_m=gps_accuracy_m,
        speed_kmh=speed_kmh,
        direction_deg=direction_deg,
        captured_at=captured_at,
        source=source.value,
        score=score,
        confidence=confidence,
        detected=detected,
        needs_review=not detected,
        boxes=result.get("boxes") or [],
        inference_ms=result.get("inference_ms"),
        status="new",
        device_id=device_id,
    )
    db.add(report)
    try:
        await db.flush()
    except IntegrityError:  # the same device_report_id raced in on another request
        await db.rollback()
        await storage.delete(photo_url)
        existing = await db.scalar(select(Report).where(Report.device_report_id == device_report_id))
        response.status_code = http.HTTP_200_OK
        return await _create_response(db, existing)

    if detected or force:
        await assign_report(db, report)
    await db.commit()
    background.add_task(jobs.kick)
    if blurred:
        logger.info("Report %s: blurred %d face/plate region(s)", report_id, blurred)
    return await _create_response(db, report)


@router.get("/reports/{device_report_id}", response_model=ReportDetail)
async def get_report(device_report_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """The tracker for one report. Knowing the device_report_id (a random UUID
    generated on the phone) is what proves the caller sent it."""
    r = await db.scalar(select(Report).where(Report.device_report_id == device_report_id))
    if r is None:
        raise HTTPException(http.HTTP_404_NOT_FOUND, "Unknown device_report_id")
    p = await db.get(Pothole, r.pothole_id) if r.pothole_id else None
    offices = await office_map(db)
    return {
        **device_report(r, p, offices),
        "sheet_summary": sheet_summary(p),
        "timeline": timeline(p, r),
    }


@router.get("/devices/{device_id}/reports", response_model=list[DeviceReport])
async def device_reports(device_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Every report this phone sent, newest first, with its pothole's status."""
    rows = (
        await db.execute(
            select(Report, Pothole)
            .outerjoin(Pothole, Pothole.pothole_id == Report.pothole_id)
            .where(Report.device_id == device_id)
            .order_by(Report.created_at.desc())
            .limit(500)
        )
    ).all()
    offices = await office_map(db)
    return [device_report(r, p, offices) for r, p in rows]


@router.post(
    "/detect",
    response_model=Detection,
    dependencies=[Depends(limit("detect_device", 120, 60, by="device"))],
)
async def detect(
    frame: UploadFile = File(...),
    source: ReportSource = Form(ReportSource.DRIVING_MODE),
    device_id: str | None = Form(None),
) -> dict:
    """Driving mode: scores one camera frame and forgets it (nothing stored).
    The phone uploads a real report only after 3 positive frames in a row."""
    raw = await read_photo(frame)
    result = await run_inference_async(raw, source.value)
    detected = result.get("score") is not None and (result.get("confidence") or 0) >= settings.min_confidence
    return {"detected": detected, **{k: result.get(k) for k in ("score", "confidence", "boxes", "inference_ms")}}


# --- Deprecated Sprint 1 routes (kept one sprint for old clients) ------------

@router.patch("/reports/{report_id}", response_model=StatusUpdateResponse, deprecated=True)
async def update_report_status(
    report_id: uuid.UUID,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    office: Office = Depends(require_office),
) -> dict:
    """Use PATCH /potholes/{pothole_id}. Changes the status of the report's pothole."""
    r = await db.get(Report, report_id)
    if r is None or r.pothole_id is None:
        raise HTTPException(http.HTTP_404_NOT_FOUND, "Unknown report_id")
    p = await db.get(Pothole, r.pothole_id)
    ensure_scope(office, p)
    try:
        await set_status(db, p, body.status, f"office:{office.code}", body.note)
    except InvalidTransition as exc:
        raise HTTPException(http.HTTP_409_CONFLICT, str(exc)) from exc
    await db.commit()
    return {"report_id": report_id, "pothole_id": p.pothole_id, "status": p.status, "updated_at": p.updated_at}

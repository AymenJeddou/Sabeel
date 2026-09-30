"""
POST /reports, GET /reports/{device_report_id}, PATCH /reports/{report_id}
Sprint1_Action_Plan.md Section 4.5, wired to the real database, WP1's vision
model, WP2's RAG service, and the real PostGIS dedup check.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db import get_db
from backend.app.db_models import Report
from backend.app.dedup import find_or_join_cluster
from backend.app.insights import reverse_geocode, summarize_all
from backend.app.rag_client import generate as rag_generate
from backend.app.schemas import (
    ReportCreateResponse,
    ReportDetail,
    ReportSource,
    ReportSummary,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from backend.app.status import ReportStatus, is_valid_transition
from backend.app.vision_client import meets_sheet_threshold, run_inference

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])

STATIC_PHOTOS_DIR = Path(__file__).resolve().parent.parent / "static" / "photos"


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
    # Optional, additive: the phone's persistent id, for "Mes Rapports" and support chat.
    device_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> ReportCreateResponse:
    report_id = uuid.uuid4()
    photo_bytes = await photo.read()

    STATIC_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    photo_path = STATIC_PHOTOS_DIR / f"{report_id}.jpg"
    photo_path.write_bytes(photo_bytes)
    photo_url = f"/static/photos/{report_id}.jpg"

    try:
        inference_result = run_inference(photo_bytes)
    except Exception:
        logger.exception("Vision inference failed; treating as no detection.")
        inference_result = {"score": None, "confidence": None}

    score = inference_result.get("score")
    confidence = inference_result.get("confidence")

    cluster_id = await find_or_join_cluster(db, lat, lon, settings.max_dedup_distance_m)
    report_status = ReportStatus.CONFIRMED if cluster_id else ReportStatus.NEW
    if cluster_id is None and report_status == ReportStatus.CONFIRMED:
        cluster_id = uuid.uuid4()

    sheet_text = None
    target_office = None

    if report_status == ReportStatus.CONFIRMED and meets_sheet_threshold(score, settings.score_threshold_for_sheet):
        rag_result = await rag_generate(lat=lat, lon=lon, score=score)
        if rag_result:
            sheet_text = rag_result.get("sheet_text")
            target_office = rag_result.get("target_office")
            report_status = ReportStatus.SHEET_SENT
        else:
            logger.warning("RAG generation failed/unavailable; leaving status at 'confirmed'.")

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
        source=source,
        score=score,
        confidence=confidence,
        status=report_status,
        cluster_id=cluster_id,
        sheet_text=sheet_text,
        target_office=target_office,
        device_id=device_id,
        address=await reverse_geocode(lat, lon),
    )
    db.add(report)
    await db.commit()

    return ReportCreateResponse(
        report_id=report_id,
        device_report_id=device_report_id,
        status=report_status,
        score=score,
        sheet_summary=sheet_text,
        target_office=target_office,
    )


@router.get("/reports", response_model=list[ReportSummary])
async def list_reports(
    device_id: str | None = None,
    status: ReportStatus | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Every report with dashboard fields (ref, cluster size, deadline, priority),
    newest first. Cluster sizes count across all reports, not just the filtered ones."""
    rows = list((await db.execute(select(Report).order_by(Report.created_at.desc()))).scalars())
    return [
        s
        for row, s in zip(rows, summarize_all(rows))
        if (device_id is None or row.device_id == device_id) and (status is None or s["status"] == status)
    ]


@router.get("/reports/{device_report_id}", response_model=ReportDetail)
async def get_report(device_report_id: str, db: AsyncSession = Depends(get_db)) -> ReportDetail:
    result = await db.execute(
        select(Report).where(Report.device_report_id == device_report_id).order_by(Report.created_at.desc())
    )
    report = result.scalars().first()
    if report is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Unknown device_report_id")

    return ReportDetail(
        report_id=report.report_id,
        status=report.status,
        score=report.score,
        sheet_summary=report.sheet_text,
    )


@router.patch("/reports/{report_id}", response_model=StatusUpdateResponse)
async def update_report_status(
    report_id: uuid.UUID, body: StatusUpdateRequest, db: AsyncSession = Depends(get_db)
) -> StatusUpdateResponse:
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Unknown report_id")

    if not is_valid_transition(report.status, body.status):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Transition from '{report.status.value}' to '{body.status.value}' is not forward",
        )

    report.status = body.status
    report.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return StatusUpdateResponse(report_id=report_id, status=body.status, updated_at=report.updated_at)

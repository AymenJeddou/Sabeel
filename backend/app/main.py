"""TEMPORARY INSURANCE GLUE -- see README.md and GitHub issue #4.

Minimal FastAPI backend wiring WP1's infer() + WP2's RAG generate() together,
approximating Section 4.5's endpoint shapes with SQLite instead of
Supabase/PostGIS. Built so a real end-to-end mobile demo exists regardless of
WP3's own timeline -- Jasseur/Tharaa can replace these files in place.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from . import config, db
from .dedup import find_or_join_cluster
from .rag_client import generate as rag_generate
from .schemas import (
    MapPoint,
    ReportCreatedResponse,
    ReportStatusResponse,
    StatusUpdateRequest,
    StatusUpdateResponse,
)
from .vision_client import meets_sheet_threshold, run_inference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RoadScan Glue Backend (temporary, see issue #4)")

config.STATIC_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(config.STATIC_PHOTOS_DIR.parent)), name="static")


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/reports", response_model=ReportCreatedResponse, status_code=201)
async def create_report(
    device_report_id: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    gps_accuracy_m: float = Form(0.0),
    speed_kmh: float = Form(0.0),
    direction_deg: float = Form(0.0),
    captured_at: str = Form(...),
    source: str = Form("manual"),
    photo: UploadFile = File(...),
) -> ReportCreatedResponse:
    report_id = str(uuid.uuid4())
    photo_bytes = await photo.read()

    photo_path = config.STATIC_PHOTOS_DIR / f"{report_id}.jpg"
    photo_path.write_bytes(photo_bytes)
    photo_url = f"/static/photos/{report_id}.jpg"

    try:
        inference_result = run_inference(photo_bytes)
    except Exception:
        logger.exception("Vision inference failed; treating as no detection.")
        inference_result = {"score": None, "confidence": None}

    score = inference_result.get("score")
    confidence = inference_result.get("confidence")

    now = _now_iso()
    sheet_text = None
    target_office = None

    with db.get_conn() as conn:
        cluster_id = find_or_join_cluster(conn, lat, lon)
        status = "confirmed" if cluster_id else "new"
        if cluster_id is None and status == "confirmed":
            cluster_id = str(uuid.uuid4())

        if status == "confirmed" and meets_sheet_threshold(score):
            rag_result = rag_generate(lat=lat, lon=lon, score=score)
            if rag_result:
                sheet_text = rag_result.get("sheet_text")
                target_office = rag_result.get("target_office")
                status = "sheet_sent"
            else:
                logger.warning("RAG generation failed/unavailable; leaving status at 'confirmed'.")

        conn.execute(
            """
            INSERT INTO reports (
                report_id, device_report_id, photo_url, lat, lon, gps_accuracy_m,
                speed_kmh, direction_deg, captured_at, source, score, confidence,
                status, cluster_id, sheet_text, target_office, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id, device_report_id, photo_url, lat, lon, gps_accuracy_m,
                speed_kmh, direction_deg, captured_at, source, score, confidence,
                status, cluster_id, sheet_text, target_office, now, now,
            ),
        )

    return ReportCreatedResponse(
        report_id=report_id, device_report_id=device_report_id, status=status, score=score
    )


@app.get("/map", response_model=list[MapPoint])
def get_map() -> list[MapPoint]:
    with db.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT report_id, lat, lon, score, status, cluster_id, created_at
            FROM reports
            WHERE cluster_id IS NULL
               OR report_id IN (
                   SELECT report_id FROM reports r2
                   WHERE r2.cluster_id = reports.cluster_id
                   ORDER BY r2.created_at DESC LIMIT 1
               )
            """
        ).fetchall()
    return [
        MapPoint(report_id=r["report_id"], lat=r["lat"], lon=r["lon"], score=r["score"],
                  status=r["status"], cluster_id=r["cluster_id"])
        for r in rows
    ]


@app.get("/reports/{device_report_id}", response_model=ReportStatusResponse)
def get_report_status(device_report_id: str) -> ReportStatusResponse:
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT report_id, status, score, sheet_text FROM reports WHERE device_report_id = ? ORDER BY created_at DESC LIMIT 1",
            (device_report_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown device_report_id")
    return ReportStatusResponse(
        report_id=row["report_id"], status=row["status"], score=row["score"],
        sheet_summary=row["sheet_text"],
    )


@app.patch("/reports/{report_id}", response_model=StatusUpdateResponse)
def update_report_status(report_id: str, body: StatusUpdateRequest) -> StatusUpdateResponse:
    if body.status not in config.STATUS_ORDER:
        raise HTTPException(status_code=422, detail="Invalid status value")

    with db.get_conn() as conn:
        row = conn.execute("SELECT status FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Unknown report_id")

        current_index = config.STATUS_ORDER.index(row["status"])
        target_index = config.STATUS_ORDER.index(body.status)
        if target_index <= current_index:
            raise HTTPException(status_code=409, detail="Status transitions must move forward")

        now = _now_iso()
        conn.execute(
            "UPDATE reports SET status = ?, updated_at = ? WHERE report_id = ?",
            (body.status, now, report_id),
        )

    return StatusUpdateResponse(report_id=report_id, status=body.status, updated_at=now)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)

"""Turns rows into API dicts. Public shapes are filtered again by the Pydantic
allow-list models in schemas.py; officer shapes carry everything."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import sla
from backend.app.db_models import Job, Office, Pothole, Report, ReportEvent
from backend.app.potholes import is_open, now_utc


async def office_map(db: AsyncSession) -> dict[uuid.UUID, Office]:
    return {o.office_id: o for o in (await db.execute(select(Office))).scalars()}


def office_name(offices: dict[uuid.UUID, Office], office_id: uuid.UUID | None) -> str | None:
    o = offices.get(office_id) if office_id else None
    return o.name if o else None


def sla_fields(p: Pothole, now: datetime | None = None) -> dict[str, Any]:
    now = now or now_utc()
    level = sla.level(p.confirmed_at, p.sla_due_at, now, is_open(p))
    return {
        "sla_due_at": p.sla_due_at,
        "sla_level": level,
        "overdue": level == "overdue",
        "overdue_by_hours": sla.overdue_by_hours(p.sla_due_at, now) if level == "overdue" else 0.0,
    }


def public_pothole(p: Pothole, offices: dict) -> dict[str, Any]:
    return {
        "pothole_id": p.pothole_id,
        "ref": p.ref,
        "lat": p.lat,
        "lon": p.lon,
        "status": p.status,
        "severity": p.severity,
        "report_count": p.report_count,
        "device_count": p.device_count,
        "confirm_count": p.confirm_count,
        "fixed_ok_count": p.fixed_ok_count,
        "not_fixed_count": p.not_fixed_count,
        "road_name": p.road_name,
        "address_label": p.address_label,
        "municipality": p.municipality,
        "region": p.region,
        "target_office": office_name(offices, p.target_office_id),
        "sheet_status": p.sheet_status,
        "sla_level": sla_fields(p)["sla_level"],
        "fix_verified": p.fix_verified,
        "created_on": p.created_at.date(),
        "confirmed_on": p.confirmed_at.date() if p.confirmed_at else None,
        "fixed_on": p.fixed_at.date() if p.fixed_at else None,
    }


def map_item(p: Pothole) -> dict[str, Any]:
    return {
        "pothole_id": p.pothole_id,
        "ref": p.ref,
        "lat": p.lat,
        "lon": p.lon,
        "score": p.severity,
        "status": p.status,
        "report_count": p.report_count,
        "confirm_count": p.confirm_count,
        "address_label": p.address_label,
        "created_on": p.created_at.date(),
        "report_id": None,
        "cluster_id": p.pothole_id,
    }


def queue_row(p: Pothole, offices: dict) -> dict[str, Any]:
    """One officer-queue / export row."""
    return {
        **public_pothole(p, offices),
        **sla_fields(p),
        "target_office_id": p.target_office_id,
        "priority_score": p.priority_score,
        "priority_components": p.priority_components or {},
        "road_type": p.road_type,
        "road_class": p.road_class,
        "road_ref": p.road_ref,
        "needs_review": p.needs_review,
        "not_pothole_count": p.not_pothole_count,
        "max_confidence": p.max_confidence,
        "rain_mm_48h": p.rain_mm_48h,
        "escalated_at": p.escalated_at,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "confirmed_at": p.confirmed_at,
        "fixed_at": p.fixed_at,
        "age_days": round((now_utc() - p.created_at).total_seconds() / 86400, 1),
    }


def report_brief(r: Report) -> dict[str, Any]:
    return {
        "report_id": r.report_id,
        "device_report_id": r.device_report_id,
        "device_id": r.device_id,
        "photo_url": r.photo_url,
        "lat": r.lat,
        "lon": r.lon,
        "gps_accuracy_m": r.gps_accuracy_m,
        "speed_kmh": r.speed_kmh,
        "direction_deg": r.direction_deg,
        "source": r.source,
        "score": r.score,
        "confidence": r.confidence,
        "detected": r.detected,
        "boxes": r.boxes or [],
        "captured_at": r.captured_at,
        "created_at": r.created_at,
    }


async def officer_pothole(db: AsyncSession, p: Pothole, offices: dict) -> dict[str, Any]:
    reports = (await db.execute(select(Report).where(Report.pothole_id == p.pothole_id).order_by(Report.created_at))).scalars()
    events = (
        await db.execute(select(ReportEvent).where(ReportEvent.pothole_id == p.pothole_id).order_by(ReportEvent.created_at))
    ).scalars()
    sheet_job = await db.scalar(
        select(Job).where(Job.pothole_id == p.pothole_id, Job.type == "sheet").order_by(Job.id.desc()).limit(1)
    )
    return {
        **queue_row(p, offices),
        "sheet_text": p.sheet_text,
        "sheet_edited": bool(p.sheet_text and p.sheet_text_original and p.sheet_text != p.sheet_text_original),
        "sheet_citations": p.sheet_citations or [],
        "sheet_generated_at": p.sheet_generated_at,
        "sheet_approved_at": p.sheet_approved_at,
        "sheet_approved_by": p.sheet_approved_by,
        "sheet_hash": p.sheet_hash,
        "sheet_job": (
            {"status": sheet_job.status, "attempts": sheet_job.attempts, "last_error": sheet_job.last_error,
             "next_attempt_at": sheet_job.next_attempt_at}
            if sheet_job else None
        ),
        "fixed_proof_url": p.fixed_proof_url,
        "fixed_note": p.fixed_note,
        "fix_check": p.fix_check,
        "repair_method": sla.METHOD.get(p.severity or 0),
        "enrichment_source": p.enrichment_source,
        "reports": [report_brief(r) for r in reports],
        "events": [
            {"kind": e.kind, "actor": e.actor, "from_status": e.from_status, "to_status": e.to_status,
             "note": e.note, "data": e.data, "created_at": e.created_at}
            for e in events
        ],
    }


def sheet_summary(p: Pothole | None) -> str | None:
    """What a citizen may read of the sheet: only once approved, first 3 lines."""
    if not p or p.sheet_status != "approved" or not p.sheet_text:
        return None
    return "\n".join(p.sheet_text.strip().splitlines()[:3])


def timeline(p: Pothole | None, r: Report) -> list[dict[str, Any]]:
    steps = [{"status": "new", "at": r.created_at}]
    if p is None:
        return steps
    if p.confirmed_at:
        steps.append({"status": "confirmed", "at": p.confirmed_at})
    if p.sheet_approved_at:
        steps.append({"status": "sheet_sent", "at": p.sheet_approved_at})
    if p.fixed_at:
        steps.append({"status": "fixed", "at": p.fixed_at})
    if p.status in ("rejected", "reopened"):
        steps.append({"status": p.status, "at": p.reopened_at or p.updated_at})
    return steps


def device_report(r: Report, p: Pothole | None, offices: dict) -> dict[str, Any]:
    return {
        "device_report_id": r.device_report_id,
        "report_id": r.report_id,
        "pothole_id": r.pothole_id,
        "ref": p.ref if p else None,
        "status": p.status if p else r.status,
        "score": r.score,
        "severity": p.severity if p else r.score,
        "detected": r.detected,
        "sheet_status": p.sheet_status if p else None,
        "target_office": office_name(offices, p.target_office_id) if p else None,
        "address_label": p.address_label if p else r.address,
        "photo_url": r.photo_url,
        "lat": r.lat,
        "lon": r.lon,
        "created_at": r.created_at,
        "updated_at": max(r.updated_at, p.updated_at) if p else r.updated_at,
        "fixed_at": p.fixed_at if p else None,
    }

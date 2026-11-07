"""Pothole domain logic: attaching reports, confirming, status changes, audit.

Every status change goes through `set_status()`, which validates the
transition, stamps the lifecycle timestamps, writes a `report_events` row and
recomputes priority, so no code path can forget one of those.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import priority, sla
from backend.app.config import settings
from backend.app.db_models import Confirmation, Pothole, Report, ReportEvent
from backend.app.status import OPEN_STATUSES, ReportStatus as S, is_valid_transition


class InvalidTransition(Exception):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def device_key(report: Report) -> str:
    """Stable identity of the phone behind a report (legacy clients sent no device_id)."""
    return report.device_id or f"legacy:{report.device_report_id}"


def is_open(p: Pothole) -> bool:
    return S(p.status) in OPEN_STATUSES


def sheet_required(p: Pothole) -> bool:
    return (p.severity or 0) >= settings.score_threshold_for_sheet


async def record_event(
    db: AsyncSession,
    pothole: Pothole,
    actor: str,
    kind: str,
    *,
    from_status: str | None = None,
    to_status: str | None = None,
    note: str | None = None,
    data: dict[str, Any] | None = None,
    report_id: uuid.UUID | None = None,
) -> None:
    db.add(
        ReportEvent(
            pothole_id=pothole.pothole_id,
            report_id=report_id,
            actor=actor,
            kind=kind,
            from_status=from_status,
            to_status=to_status,
            note=note,
            data=data,
        )
    )


def recompute_priority(p: Pothole, now: datetime | None = None) -> None:
    now = now or now_utc()
    overdue = sla.level(p.confirmed_at, p.sla_due_at, now, is_open(p)) == "overdue"
    p.priority_score, p.priority_components = priority.compute(
        severity=p.severity,
        road_class=p.road_class or p.road_type,
        device_count=p.device_count,
        opened_at=p.created_at or now,
        now=now,
        status=p.status,
        overdue=overdue,
        rain_mm_48h=p.rain_mm_48h,
        rain_alert_mm=settings.rain_alert_mm,
    )


async def set_status(
    db: AsyncSession, p: Pothole, new: S, actor: str, note: str | None = None, *, force: bool = False
) -> None:
    """Moves a pothole to `new` or raises InvalidTransition. `force` skips the
    check (used only by the seed script to replay history)."""
    old = S(p.status)
    if not force and not is_valid_transition(old, new, sheet_required=sheet_required(p)):
        raise InvalidTransition(f"Transition from '{old.value}' to '{new.value}' is not allowed")
    now = now_utc()
    p.status = new.value
    p.updated_at = now
    if new == S.CONFIRMED:
        p.confirmed_at = p.confirmed_at or now
        p.sla_due_at = sla.due_at(p.confirmed_at, p.severity)
    elif new == S.FIXED:
        p.fixed_at = now
        p.sla_due_at = None
    elif new == S.REOPENED:
        p.reopened_at = now
        p.fixed_at = None
        p.fix_verified = False
        # A reopened pothole gets a fresh deadline from the moment it was reopened.
        p.confirmed_at = now
        p.sla_due_at = sla.due_at(now, p.severity)
    recompute_priority(p, now)
    await db.execute(update(Report).where(Report.pothole_id == p.pothole_id).values(status=new.value))
    await record_event(db, p, actor, "status", from_status=old.value, to_status=new.value, note=note)

    if new in (S.CONFIRMED, S.REOPENED):
        await queue_sheet_if_needed(db, p)


async def queue_sheet_if_needed(db: AsyncSession, p: Pothole) -> None:
    from backend.app.jobs import enqueue  # local import: jobs imports this module

    if sheet_required(p) and p.sheet_status in (None, "failed"):
        p.sheet_status = "queued"
        await enqueue(db, p.pothole_id, "sheet")


async def find_nearby(db: AsyncSession, lat: float, lon: float, radius_m: float, statuses: list[str]) -> Pothole | None:
    row = (
        await db.execute(
            text(
                """
                SELECT pothole_id FROM potholes
                WHERE status = ANY(:statuses)
                  AND ST_DWithin(geography(ST_SetSRID(ST_MakePoint(lon, lat), 4326)),
                                 geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)), :r)
                ORDER BY ST_Distance(geography(ST_SetSRID(ST_MakePoint(lon, lat), 4326)),
                                     geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)))
                LIMIT 1
                """
            ),
            {"lat": lat, "lon": lon, "r": radius_m, "statuses": statuses},
        )
    ).first()
    return await db.get(Pothole, row[0]) if row else None


async def distinct_devices(db: AsyncSession, pothole_id: uuid.UUID) -> set[str]:
    """Phones that reported it or tapped "I see it too": each counts once."""
    reports = (await db.execute(select(Report).where(Report.pothole_id == pothole_id))).scalars()
    seen = (
        await db.execute(
            select(Confirmation.device_id).where(Confirmation.pothole_id == pothole_id, Confirmation.kind == "seen")
        )
    ).scalars()
    return {device_key(r) for r in reports} | set(seen)


async def refresh_aggregates(db: AsyncSession, p: Pothole) -> None:
    """Recomputes counts, severity and position from the attached reports."""
    reports = list((await db.execute(select(Report).where(Report.pothole_id == p.pothole_id))).scalars())
    p.report_count = len(reports)
    p.device_count = len(await distinct_devices(db, p.pothole_id))
    p.confirm_count = await db.scalar(
        select(func.count()).where(Confirmation.pothole_id == p.pothole_id, Confirmation.kind == "seen")
    ) or 0
    scores = sorted(r.score for r in reports if r.detected and r.score)
    # Upper median: robust to one exaggerated close-up, but never rounds a 4/5 tie down.
    p.severity = scores[len(scores) // 2] if scores else p.severity
    confs = [r.confidence for r in reports if r.confidence is not None]
    p.max_confidence = max(confs) if confs else p.max_confidence
    if reports:
        # Weighted mean position: a 3 m GPS fix counts 16x more than a 12 m one.
        w = [1 / max(r.gps_accuracy_m or 10, 3) ** 2 for r in reports]
        p.lat = sum(r.lat * wi for r, wi in zip(reports, w)) / sum(w)
        p.lon = sum(r.lon * wi for r, wi in zip(reports, w)) / sum(w)
    if any(r.detected for r in reports) and p.status == S.NEW.value:
        p.needs_review = False
    p.updated_at = now_utc()
    recompute_priority(p)


async def evaluate_confirmation(db: AsyncSession, p: Pothole) -> bool:
    """A `new` pothole becomes `confirmed` once MIN_DISTINCT_DEVICES_TO_CONFIRM
    different phones back it and the model saw a pothole in at least one photo.
    Without a detection, an officer has to confirm it by hand (needs_review)."""
    if p.status != S.NEW.value or p.device_count < settings.min_distinct_devices_to_confirm:
        return False
    detected = await db.scalar(
        select(func.count()).where(Report.pothole_id == p.pothole_id, Report.detected.is_(True))
    )
    if not detected:
        p.needs_review = True
        return False
    await set_status(db, p, S.CONFIRMED, "system", f"{p.device_count} appareils distincts")
    return True


async def assign_report(db: AsyncSession, report: Report) -> Pothole:
    """Attaches a report to the nearest open pothole within MAX_DEDUP_DISTANCE_M,
    or to a recently fixed one there (which counts as "still there"), or
    creates a new pothole. The report must already be added to the session."""
    from backend.app.jobs import enqueue

    radius = settings.max_dedup_distance_m
    actor = f"device:{device_key(report)}"
    p = await find_nearby(db, report.lat, report.lon, radius, [s.value for s in OPEN_STATUSES])
    reopen_candidate = None
    if p is None:
        fixed = await find_nearby(db, report.lat, report.lon, radius, [S.FIXED.value])
        if fixed and fixed.fixed_at and fixed.fixed_at > now_utc() - timedelta(days=settings.reopen_window_days):
            p = reopen_candidate = fixed

    created = p is None
    if created:
        p = Pothole(
            pothole_id=uuid.uuid4(),
            status=S.NEW.value,
            lat=report.lat,
            lon=report.lon,
            needs_review=not report.detected,
            created_at=now_utc(),
            updated_at=now_utc(),
            priority_components={},
        )
        db.add(p)
        await db.flush()
        await record_event(db, p, actor, "created", to_status=S.NEW.value, report_id=report.report_id)
        await enqueue(db, p.pothole_id, "enrich")

    report.pothole_id = p.pothole_id
    report.status = p.status
    await db.flush()
    if not created:
        await record_event(db, p, actor, "report_added", report_id=report.report_id)
    if reopen_candidate is not None:
        await add_confirmation(db, p, device_key(report), "not_fixed", report.lat, report.lon, report.gps_accuracy_m)
    await refresh_aggregates(db, p)
    await evaluate_confirmation(db, p)
    return p


async def add_confirmation(
    db: AsyncSession, p: Pothole, device_id: str, kind: str, lat: float | None, lon: float | None, acc: float | None
) -> bool:
    """Stores one (pothole, device, kind) tap and applies its effect. Returns
    False if this device already sent this kind (idempotent no-op)."""
    exists = await db.scalar(
        select(Confirmation.id).where(
            Confirmation.pothole_id == p.pothole_id, Confirmation.device_id == device_id, Confirmation.kind == kind
        )
    )
    if exists:
        return False
    db.add(Confirmation(pothole_id=p.pothole_id, device_id=device_id, kind=kind, lat=lat, lon=lon, gps_accuracy_m=acc))
    await db.flush()
    await record_event(db, p, f"device:{device_id}", f"confirmation_{kind}")

    async def count(k: str) -> int:
        return await db.scalar(
            select(func.count(func.distinct(Confirmation.device_id))).where(
                Confirmation.pothole_id == p.pothole_id, Confirmation.kind == k
            )
        ) or 0

    if kind == "seen":
        await refresh_aggregates(db, p)
        await evaluate_confirmation(db, p)
    elif kind == "not_fixed":
        p.not_fixed_count = await count("not_fixed")
        if p.status == S.FIXED.value and p.not_fixed_count >= settings.reopen_min_devices:
            await set_status(db, p, S.REOPENED, "system", f"{p.not_fixed_count} citoyens : toujours là")
    elif kind == "fixed_ok":
        p.fixed_ok_count = await count("fixed_ok")
        p.fix_verified = p.fixed_ok_count >= 1 and not (p.fix_check or {}).get("detected", False)
    elif kind == "not_pothole":
        p.not_pothole_count = await count("not_pothole")
        if p.not_pothole_count >= settings.not_pothole_min_devices and not p.needs_review:
            p.needs_review = True
            from backend.app.feedback import label_pothole

            await label_pothole(db, p, "not_pothole", "citizen", note="signalé par plusieurs citoyens")
    p.updated_at = now_utc()
    return True

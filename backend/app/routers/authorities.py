"""Officer routes: who am I, queue, export, analytics, route planner, weather.

All scoped to the token's office; the ministry sees every office.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import analytics, routing, sla, weather
from backend.app.auth import require_office, resolve_office_id, scope_filter
from backend.app.config import settings
from backend.app.db import get_db
from backend.app.db_models import Office, Pothole, Report
from backend.app.feedback import false_positive_rate
from backend.app.potholes import now_utc
from backend.app.ratelimit import limit
from backend.app.routers.map import parse_sev, state_filter
from backend.app.serialize import office_map, queue_row

router = APIRouter(tags=["authorities"], dependencies=[Depends(limit("officer", 120, 60, by="token"))])
EXPORT_CAP = 10_000


@router.get("/auth/me")
async def me(office: Office = Depends(require_office), db: AsyncSession = Depends(get_db)) -> dict:
    offices = await office_map(db)
    parent = offices.get(office.parent_office_id) if office.parent_office_id else None
    return {
        "office_id": office.office_id,
        "code": office.code,
        "name": office.name,
        "kind": office.kind,
        "region": office.region,
        "lat": office.lat,
        "lon": office.lon,
        "is_ministry": office.is_ministry,
        "parent": parent.name if parent else None,
        "offices": [
            {"office_id": o.office_id, "code": o.code, "name": o.name, "kind": o.kind, "region": o.region}
            for o in offices.values()
        ] if office.is_ministry else [],
    }


async def scoped_potholes(
    db: AsyncSession,
    office: Office,
    *,
    office_id: uuid.UUID | None = None,
    status: str | None = None,
    sev: str | None = None,
    region: str | None = None,
    needs_review: bool | None = None,
    sheet_status: str | None = None,
) -> list[Pothole]:
    statuses = [*state_filter("all"), "rejected"] if status == "any" else state_filter(status)
    q = select(Pothole).where(scope_filter(office), Pothole.status.in_(statuses))
    if office_id and office_id != office.office_id:
        q = q.where(Pothole.target_office_id == office_id)
    if (levels := parse_sev(sev)) is not None:
        q = q.where(Pothole.severity.in_(levels))
    if region:
        q = q.where(Pothole.region == region)
    if needs_review is not None:
        q = q.where(Pothole.needs_review.is_(needs_review))
    if sheet_status:
        q = q.where(Pothole.sheet_status == sheet_status)
    return list((await db.execute(q)).scalars())


SORTS = {
    "priority": lambda r: -r["priority_score"],
    "age": lambda r: r["created_at"],
    "severity": lambda r: -(r["severity"] or 0),
    "deadline": lambda r: (r["sla_due_at"] is None, r["sla_due_at"] or r["created_at"]),
}


async def queue_rows(db: AsyncSession, office: Office, office_id: uuid.UUID | None, filters: dict[str, Any]) -> list[dict]:
    overdue = filters.pop("overdue", None)
    sort = filters.pop("sort", "priority")
    potholes = await scoped_potholes(db, office, office_id=office_id, **filters)
    offices = await office_map(db)
    rows = [queue_row(p, offices) for p in potholes]
    if overdue is not None:
        rows = [r for r in rows if r["overdue"] == overdue]
    return sorted(rows, key=SORTS.get(sort, SORTS["priority"]))


def _filters(status, sev, region, needs_review, sheet_status, overdue, sort) -> dict[str, Any]:
    return {"status": status, "sev": sev, "region": region, "needs_review": needs_review,
            "sheet_status": sheet_status, "overdue": overdue, "sort": sort}


@router.get("/authorities/{office_id}/queue")
async def queue(
    office_id: str,
    status: str | None = Query(None, description="open | fixed | all | rejected | comma list"),
    sev: str | None = None,
    region: str | None = None,
    needs_review: bool | None = None,
    sheet_status: str | None = None,
    overdue: bool | None = None,
    sort: str = Query("priority", pattern="^(priority|age|severity|deadline)$"),
    limit_: int = Query(50, alias="limit", ge=1, le=500),
    cursor: int = Query(0, ge=0, description="offset returned as next_cursor"),
    office: Office = Depends(require_office),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """The office's to-do list, highest priority first. `office_id` may be `me`."""
    wanted = resolve_office_id(office, office_id)
    rows = await queue_rows(db, office, wanted, _filters(status or "open", sev, region, needs_review, sheet_status, overdue, sort))
    page = rows[cursor : cursor + limit_]
    return {"items": page, "total": len(rows), "next_cursor": cursor + limit_ if cursor + limit_ < len(rows) else None}


EXPORT_COLUMNS = [
    "ref", "pothole_id", "status", "severity", "priority_score", "lat", "lon", "address_label", "road_ref", "road_name",
    "road_class", "municipality", "region", "target_office", "report_count", "device_count", "confirm_count",
    "sheet_status", "sla_due_at", "sla_level", "overdue_by_hours", "fix_verified", "needs_review", "created_at",
    "confirmed_at", "fixed_at",
]


def csv_safe(v: Any) -> Any:
    """Road names come from OpenStreetMap, which anyone can edit: text starting with = + - @
    would run as a formula when an officer opens the export in Excel, so it gets a leading '."""
    return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


@router.get("/export")
async def export(
    format: str = Query("csv", pattern="^(csv|geojson)$"),
    status: str | None = None,
    sev: str | None = None,
    region: str | None = None,
    needs_review: bool | None = None,
    sheet_status: str | None = None,
    overdue: bool | None = None,
    sort: str = "priority",
    office: Office = Depends(require_office),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Same rows as the queue with the same filters, capped at 10,000.
    CSV columns = EXPORT_COLUMNS; GeoJSON = Point features ([lon, lat]) with the
    same properties."""
    rows = (await queue_rows(db, office, None, _filters(status or "all", sev, region, needs_review, sheet_status, overdue, sort)))[:EXPORT_CAP]
    stamp = now_utc().strftime("%Y%m%d")

    def cell(v: Any) -> Any:
        return v.isoformat().replace("+00:00", "Z") if hasattr(v, "isoformat") else str(v) if isinstance(v, uuid.UUID) else v

    if format == "geojson":
        def features():
            yield '{"type":"FeatureCollection","features":['
            for i, r in enumerate(rows):
                feature = {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                    "properties": {c: cell(r[c]) for c in EXPORT_COLUMNS if c not in ("lat", "lon")},
                }
                yield ("," if i else "") + json.dumps(feature, ensure_ascii=False)
            yield "]}"

        return StreamingResponse(features(), media_type="application/geo+json",
                                 headers={"Content-Disposition": f'attachment; filename="sabeel-{stamp}.geojson"'})

    def lines():
        buf = io.StringIO()
        writer = csv.writer(buf)
        buf.write("﻿")  # Excel opens UTF-8 (accents, Arabic) correctly with a BOM
        writer.writerow(EXPORT_COLUMNS)
        for r in rows:
            writer.writerow([csv_safe(cell(r[c])) for c in EXPORT_COLUMNS])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()
        yield buf.getvalue()

    return StreamingResponse(lines(), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="sabeel-{stamp}.csv"'})


# --- Analytics (issue #29) ---------------------------------------------------

async def _analytics_rows(db, office, office_param, region) -> list[Pothole]:
    wanted = resolve_office_id(office, office_param) if office_param else None
    rows = await scoped_potholes(db, office, office_id=wanted, status="any", region=region)
    return rows


def _period(rows: list[Pothole], date_from: str | None, date_to: str | None) -> list[Pothole]:
    from datetime import date

    lo = date.fromisoformat(date_from) if date_from else None
    hi = date.fromisoformat(date_to) if date_to else None
    return [p for p in rows if (lo is None or p.created_at.date() >= lo) and (hi is None or p.created_at.date() <= hi)]


@router.get("/analytics/summary")
async def analytics_summary(
    from_: str | None = Query(None, alias="from"), to: str | None = None, office_param: str | None = Query(None, alias="office"),
    region: str | None = None, office: Office = Depends(require_office), db: AsyncSession = Depends(get_db),
) -> dict:
    rows = _period(await _analytics_rows(db, office, office_param, region), from_, to)
    return analytics.summary(rows, now_utc(), await false_positive_rate(db))


@router.get("/analytics/time-to-fix")
async def analytics_time_to_fix(
    from_: str | None = Query(None, alias="from"), to: str | None = None, office_param: str | None = Query(None, alias="office"),
    region: str | None = None, office: Office = Depends(require_office), db: AsyncSession = Depends(get_db),
) -> dict:
    rows = _period(await _analytics_rows(db, office, office_param, region), from_, to)
    offices = await office_map(db)
    return {
        "by_office": analytics.time_to_fix(rows, lambda p: offices[p.target_office_id].name if p.target_office_id in offices else None),
        "by_region": analytics.time_to_fix(rows, lambda p: p.region),
        "by_road_class": analytics.time_to_fix(rows, lambda p: p.road_class),
    }


@router.get("/analytics/hotspots")
async def analytics_hotspots(
    office_param: str | None = Query(None, alias="office"), region: str | None = None,
    office: Office = Depends(require_office), db: AsyncSession = Depends(get_db),
) -> dict:
    return analytics.hotspots(await _analytics_rows(db, office, office_param, region))


@router.get("/analytics/trend")
async def analytics_trend(
    weeks: int = Query(12, ge=2, le=52), office_param: str | None = Query(None, alias="office"), region: str | None = None,
    office: Office = Depends(require_office), db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return analytics.trend(await _analytics_rows(db, office, office_param, region), now_utc(), weeks)


@router.get("/analytics/channels")
async def analytics_channels(office: Office = Depends(require_office), db: AsyncSession = Depends(get_db)) -> dict:
    """Reports per capture channel (app photo, driving mode, web)."""
    q = select(Report.source).join(Pothole, Pothole.pothole_id == Report.pothole_id).where(scope_filter(office))
    from collections import Counter

    return dict(Counter((await db.execute(q)).scalars()))


# --- Route planner and weather (features) -----------------------------------

@router.get("/authorities/{office_id}/route")
async def route(
    office_id: str,
    start_lat: float | None = None,
    start_lon: float | None = None,
    max_stops: int = Query(10, ge=1, le=25),
    min_severity: int = Query(1, ge=1, le=5),
    office: Office = Depends(require_office),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Today's repair tour: the top `max_stops` open potholes by priority,
    ordered into a driving route from the start point (default: the office)."""
    wanted = resolve_office_id(office, office_id)
    potholes = await scoped_potholes(db, office, office_id=wanted, status="open")
    potholes = [p for p in potholes if (p.severity or 1) >= min_severity and p.status != "new"]
    potholes = sorted(potholes, key=lambda p: -p.priority_score)[:max_stops]
    if start_lat is None or start_lon is None:
        start_lat, start_lon = (office.lat or 36.8065), (office.lon or 10.1815)
    plan = await routing.plan((start_lat, start_lon), [(p.lat, p.lon) for p in potholes])
    offices = await office_map(db)
    stops = []
    for n, i in enumerate(plan["order"], 1):
        p = potholes[i]
        stops.append({**queue_row(p, offices), "stop": n, "method": sla.METHOD.get(p.severity or 0)})
    return {**plan, "start": {"lat": start_lat, "lon": start_lon}, "stops": stops}


@router.get("/weather")
async def weather_alert(office: Office = Depends(require_office), db: AsyncSession = Depends(get_db)) -> dict:
    """48 h rain forecast at the office and the potholes it puts at risk."""
    lat, lon = office.lat or 36.8065, office.lon or 10.1815
    data = await weather.forecast(lat, lon)
    rain = weather.rain_next_48h(data) if data else None
    open_ = await scoped_potholes(db, office, status="open")
    at_risk = [p for p in open_ if (p.severity or 0) >= 3 and (p.rain_mm_48h or rain or 0) >= settings.rain_alert_mm]
    daily = (data or {}).get("daily", {})
    return {
        "available": data is not None,
        "rain_mm_48h": rain,
        "alert": rain is not None and rain >= settings.rain_alert_mm,
        "threshold_mm": settings.rain_alert_mm,
        "days": [
            {"date": d, "rain_mm": r, "probability": pr}
            for d, r, pr in zip(daily.get("time", []), daily.get("precipitation_sum", []), daily.get("precipitation_probability_max", []))
        ],
        "at_risk": len(at_risk),
        "at_risk_refs": [p.ref for p in sorted(at_risk, key=lambda p: -p.priority_score)[:10]],
    }


@router.get("/offices")
async def offices(office: Office = Depends(require_office), db: AsyncSession = Depends(get_db)) -> list[dict]:
    if not office.is_ministry:
        raise HTTPException(http.HTTP_403_FORBIDDEN, "Ministry only")
    return [{"office_id": o.office_id, "code": o.code, "name": o.name, "kind": o.kind, "region": o.region}
            for o in (await office_map(db)).values()]

"""GET /map: one row per pothole (no photos, no device data), for the mobile
map. Filters: bbox, sev, state, region, office."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.db_models import Pothole
from backend.app.ratelimit import limit
from backend.app.schemas import MapItem
from backend.app.serialize import map_item
from backend.app.status import OPEN_STATUSES

router = APIRouter(tags=["map"])
MAX_ROWS = 10_000


def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = bbox.split(",")
    if len(parts) != 4:
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "bbox must be 'minLon,minLat,maxLon,maxLat'")
    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "bbox values must be numbers") from exc
    if min_lon > max_lon or min_lat > max_lat:
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "bbox min must be <= max")
    return min_lon, min_lat, max_lon, max_lat


def parse_sev(sev: str | None) -> list[int] | None:
    """'4,5' -> [4, 5]; '3-5' -> [3, 4, 5]."""
    if not sev:
        return None
    try:
        if "-" in sev:
            lo, hi = (int(x) for x in sev.split("-", 1))
            return list(range(lo, hi + 1))
        return [int(x) for x in sev.split(",")]
    except ValueError as exc:
        raise HTTPException(http.HTTP_422_UNPROCESSABLE_CONTENT, "sev must look like '4,5' or '3-5'") from exc


def state_filter(state: str | None) -> list[str]:
    """'open' | 'fixed' | 'all' | a comma list of statuses. Default: everything but rejected."""
    if not state or state == "all":
        return [*(s.value for s in OPEN_STATUSES), "fixed"]
    if state == "open":
        return [s.value for s in OPEN_STATUSES]
    return state.split(",")


def map_query(bbox: str | None, sev: str | None, state: str | None, region: str | None, office: uuid.UUID | None):
    q = select(Pothole).where(Pothole.status.in_(state_filter(state)))
    if bbox:
        min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)
        q = q.where(Pothole.lon.between(min_lon, max_lon), Pothole.lat.between(min_lat, max_lat))
    if (levels := parse_sev(sev)) is not None:
        q = q.where(Pothole.severity.in_(levels))
    if region:
        q = q.where(Pothole.region == region)
    if office:
        q = q.where(Pothole.target_office_id == office)
    return q.order_by(Pothole.priority_score.desc()).limit(MAX_ROWS)


@router.get("/map", response_model=list[MapItem], dependencies=[Depends(limit("map", 120, 60))])
async def get_map(
    bbox: str | None = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    sev: str | None = Query(default=None, description="severities, e.g. '4,5' or '3-5'"),
    state: str | None = Query(default=None, description="open | fixed | all | comma list of statuses"),
    region: str | None = None,
    office: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = (await db.execute(map_query(bbox, sev, state, region, office))).scalars()
    return [map_item(p) for p in rows]

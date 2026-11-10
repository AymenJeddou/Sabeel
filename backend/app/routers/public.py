"""Public transparency endpoints (issue #30). No login, aggregate only.

Never returned here: photos, device ids, report timestamps finer than a day,
sheet text. Responses are cached 5 minutes (in process + Cache-Control).
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import analytics
from backend.app.db import get_db
from backend.app.db_models import Pothole
from backend.app.potholes import now_utc
from backend.app.ratelimit import limit
from backend.app.routers.map import parse_bbox
from backend.app.routers.potholes import get_pothole
from backend.app.schemas import PublicMapPoint, PublicPothole, SheetVerification
from backend.app.serialize import office_map, office_name, public_pothole

router = APIRouter(prefix="/public", tags=["public"], dependencies=[Depends(limit("public", 120, 60))])
CACHE_S = 300
CACHE_MAX = 500
_cache: dict[str, tuple[float, object]] = {}


def clear_cache() -> None:
    _cache.clear()


async def _cached(key: str, build):
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_S:
        return hit[1]
    value = await build()
    now = time.monotonic()
    if len(_cache) >= CACHE_MAX:  # every map viewport is its own key: keep memory bounded
        for k in [k for k, (t, _) in _cache.items() if now - t >= CACHE_S]:
            del _cache[k]
        if len(_cache) >= CACHE_MAX:
            _cache.clear()
    _cache[key] = (now, value)
    return value


@router.get("/stats")
async def stats(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """Headline counters, median time to fix, per-region table (regions under
    5 potholes suppressed), 12-month trend and the five worst streets."""
    async def build():
        rows = list((await db.execute(select(Pothole))).scalars())
        return analytics.public_stats(rows, now_utc())

    response.headers["Cache-Control"] = f"public, max-age={CACHE_S}"
    return await _cached("stats", build)


@router.get("/map", response_model=list[PublicMapPoint])
async def public_map(
    response: Response,
    bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
    state: str = Query("all", pattern="^(all|open|fixed)$"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    async def build():
        q = select(Pothole.lat, Pothole.lon, Pothole.severity, Pothole.status).where(Pothole.status != "rejected")
        if state == "fixed":
            q = q.where(Pothole.status == "fixed")
        elif state == "open":
            q = q.where(Pothole.status != "fixed")
        if bbox:
            a, b, c, d = parse_bbox(bbox)
            q = q.where(Pothole.lon.between(a, c), Pothole.lat.between(b, d))
        # ~11 m precision: enough to find the hole, not to pinpoint a doorstep.
        return [{"lat": round(r.lat, 4), "lon": round(r.lon, 4), "severity": r.severity, "status": r.status}
                for r in (await db.execute(q.limit(20_000))).all()]

    response.headers["Cache-Control"] = f"public, max-age={CACHE_S}"
    return await _cached(f"map:{bbox}:{state}", build)


@router.get("/potholes/{pothole_id}", response_model=PublicPothole)
async def public_pothole_detail(pothole_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    return public_pothole(await get_pothole(db, pothole_id), await office_map(db))


@router.get("/potholes/{pothole_id}/verify", response_model=SheetVerification)
async def verify_sheet(pothole_id: uuid.UUID, h: str = Query(..., min_length=8, max_length=64), db: AsyncSession = Depends(get_db)) -> dict:
    """Checks the fingerprint printed on a work-order PDF (QR code)."""
    p = await get_pothole(db, pothole_id)
    valid = bool(p.sheet_hash and p.sheet_status == "approved" and p.sheet_hash.startswith(h.lower()))
    return {
        "pothole_id": p.pothole_id,
        "ref": p.ref,
        "valid": valid,
        "approved_on": p.sheet_approved_at.date() if valid and p.sheet_approved_at else None,
        "office": office_name(await office_map(db), p.target_office_id) if valid else None,
    }

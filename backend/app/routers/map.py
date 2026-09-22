"""GET /map?bbox= -- Sprint1_Action_Plan.md Section 4.5, wired to the real database.

Returns one row per confirmed pothole: the latest report in each cluster, plus
every report that hasn't been matched into a cluster yet.
"""

from fastapi import APIRouter, HTTPException, Query, status as http_status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from backend.app.db import get_db
from backend.app.schemas import MapReport

router = APIRouter(tags=["map"])

_BASE_QUERY = """
    SELECT DISTINCT ON (COALESCE(cluster_id::text, report_id::text))
        report_id, lat, lon, score, status, cluster_id
    FROM reports
    {where_clause}
    ORDER BY COALESCE(cluster_id::text, report_id::text), created_at DESC
"""


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = bbox.split(",")
    if len(parts) != 4:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="bbox must be 'minLon,minLat,maxLon,maxLat'",
        )
    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="bbox values must be numbers",
        ) from exc
    return min_lon, min_lat, max_lon, max_lat


@router.get("/map", response_model=list[MapReport])
async def get_map(
    bbox: str | None = Query(default=None, description="minLon,minLat,maxLon,maxLat"),
    db: AsyncSession = Depends(get_db),
) -> list[MapReport]:
    params: dict[str, float] = {}
    where_clause = ""
    if bbox:
        min_lon, min_lat, max_lon, max_lat = _parse_bbox(bbox)
        where_clause = "WHERE lon BETWEEN :min_lon AND :max_lon AND lat BETWEEN :min_lat AND :max_lat"
        params = {"min_lon": min_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": max_lat}

    result = await db.execute(text(_BASE_QUERY.format(where_clause=where_clause)), params)
    rows = result.mappings().all()

    return [
        MapReport(
            report_id=row["report_id"],
            lat=row["lat"],
            lon=row["lon"],
            score=row["score"],
            status=row["status"],
            cluster_id=row["cluster_id"],
        )
        for row in rows
    ]

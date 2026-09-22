"""Real <5m duplicate-merge check using PostGIS ST_DWithin against the
geography expression index created in db/schema.sql (idx_reports_geog)."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db_models import Report


async def find_or_join_cluster(db: AsyncSession, lat: float, lon: float, max_distance_m: float) -> Optional[uuid.UUID]:
    """Scans existing reports for one within max_distance_m using the real
    PostGIS geography index.

    Returns a cluster_id to use for the new report if a match is found
    (reusing the matched row's cluster_id, or minting one and backfilling the
    matched row if it didn't have one yet), else None (the new report stays
    status="new").
    """
    result = await db.execute(
        text(
            """
            SELECT report_id, cluster_id
            FROM reports
            WHERE ST_DWithin(
                geography(ST_SetSRID(ST_MakePoint(lon, lat), 4326)),
                geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)),
                :max_distance_m
            )
            ORDER BY ST_Distance(
                geography(ST_SetSRID(ST_MakePoint(lon, lat), 4326)),
                geography(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            )
            LIMIT 1
            """
        ),
        {"lat": lat, "lon": lon, "max_distance_m": max_distance_m},
    )
    row = result.first()
    if row is None:
        return None

    matched_report_id, matched_cluster_id = row

    if matched_cluster_id is not None:
        return matched_cluster_id

    new_cluster_id = uuid.uuid4()
    matched_report = await db.get(Report, matched_report_id)
    matched_report.cluster_id = new_cluster_id
    if matched_report.status.value == "new":
        matched_report.status = matched_report.status.__class__("confirmed")
    return new_cluster_id

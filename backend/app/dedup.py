"""Haversine-distance duplicate/cluster check -- explicit stand-in for PostGIS ST_DWithin."""
from __future__ import annotations

import sqlite3
from math import atan2, cos, radians, sin, sqrt
from typing import Optional

from . import config

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * atan2(sqrt(a), sqrt(1 - a))


def find_or_join_cluster(conn: sqlite3.Connection, lat: float, lon: float) -> Optional[str]:
    """Scans existing reports for one within MAX_DEDUP_DISTANCE_M.

    Returns a cluster_id to use for the new report if a match is found
    (reusing the matched row's cluster_id, or minting one and backfilling
    the matched row if it didn't have one yet), else None (this report
    stays status="new").
    """
    rows = conn.execute("SELECT report_id, lat, lon, cluster_id FROM reports").fetchall()

    for row in rows:
        distance = haversine_distance_m(lat, lon, row["lat"], row["lon"])
        if distance < config.MAX_DEDUP_DISTANCE_M:
            cluster_id = row["cluster_id"]
            if cluster_id is None:
                import uuid

                cluster_id = str(uuid.uuid4())
                conn.execute(
                    "UPDATE reports SET cluster_id = ?, status = CASE WHEN status = 'new' THEN 'confirmed' ELSE status END WHERE report_id = ?",
                    (cluster_id, row["report_id"]),
                )
            return cluster_id

    return None

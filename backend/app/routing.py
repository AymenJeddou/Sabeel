"""Crew route planner (feature): "today's repair tour" for one office.

Takes the office's highest-priority open potholes and orders them into a
driving tour from a start point (the depot or the crew's position).

1. OSRM's public /trip service solves the tour on the real road network and
   returns distance, duration and the road geometry.
2. If OSRM is unreachable, a nearest-neighbour tour improved by 2-opt on
   straight-line distances is returned instead (`engine = "fallback"`).

# ponytail: the OSRM demo server is fine for a pilot (fair-use policy); self-host
# OSRM with the Tunisia extract from Geofabrik for real crews.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.config import settings
from backend.app.geo.enrichment import haversine_m

logger = logging.getLogger(__name__)

AVG_SPEED_KMH = 25  # city traffic, used only by the fallback


def _tour_length(points: list[tuple[float, float]], order: list[int]) -> float:
    return sum(haversine_m(*points[a], *points[b]) for a, b in zip(order, order[1:]))


def plan_fallback(start: tuple[float, float], stops: list[tuple[float, float]]) -> list[int]:
    """Indices of `stops` in visiting order (open tour starting at `start`)."""
    points = [start, *stops]
    order, left = [0], set(range(1, len(points)))
    while left:
        last = points[order[-1]]
        nxt = min(left, key=lambda i: haversine_m(*last, *points[i]))
        order.append(nxt)
        left.remove(nxt)
    improved = True
    while improved:  # 2-opt: reverse any segment that shortens the tour
        improved = False
        for i in range(1, len(order) - 1):
            for j in range(i + 1, len(order)):
                candidate = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
                if _tour_length(points, candidate) + 1e-6 < _tour_length(points, order):
                    order, improved = candidate, True
    return [i - 1 for i in order[1:]]


async def plan(start: tuple[float, float], stops: list[tuple[float, float]]) -> dict[str, Any]:
    if not stops:
        return {"engine": "none", "order": [], "distance_km": 0, "duration_min": 0, "geometry": None}
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in [start, *stops])
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": settings.osm_user_agent}) as client:
            r = await client.get(
                f"{settings.osrm_url}/trip/v1/driving/{coords}",
                params={"source": "first", "roundtrip": "false", "destination": "any", "geometries": "geojson", "overview": "simplified"},
            )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != "Ok":
            raise ValueError(data.get("code"))
        # waypoints[i].waypoint_index = position of input point i in the trip.
        positions = [w["waypoint_index"] for w in data["waypoints"]]
        order = sorted(range(1, len(positions)), key=lambda i: positions[i])
        trip = data["trips"][0]
        return {
            "engine": "osrm",
            "order": [i - 1 for i in order],
            "distance_km": round(trip["distance"] / 1000, 1),
            "duration_min": round(trip["duration"] / 60),
            "geometry": trip["geometry"],
        }
    except Exception as exc:  # noqa: BLE001
        logger.info("OSRM unavailable, using the 2-opt fallback: %s", exc)
    order = plan_fallback(start, stops)
    points = [start, *[stops[i] for i in order]]
    km = sum(haversine_m(*a, *b) for a, b in zip(points, points[1:])) / 1000 * 1.3  # streets aren't straight
    return {
        "engine": "fallback",
        "order": order,
        "distance_km": round(km, 1),
        "duration_min": round(km / AVG_SPEED_KMH * 60),
        "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lat, lon in points]},
    }

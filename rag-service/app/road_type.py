"""MVP road-type resolution heuristic.

This is an explicit stand-in for real GIS/road-classification lookup (a future
WP3/GIS job). It uses a tiny hardcoded bounding-box table for a few known
Tunisian city centers; everything else falls back to "rural". A caller who
already knows the road type should pass it explicitly to generate() instead
of relying on this.
"""
from __future__ import annotations

from . import config

# (min_lat, max_lat, min_lon, max_lon) -> road_type
_CITY_BBOXES: list[tuple[float, float, float, float, str]] = [
    (36.72, 36.90, 10.05, 10.35, "urbain_principal"),  # Tunis
    (34.65, 34.80, 10.65, 10.85, "urbain_principal"),  # Sfax
    (35.78, 35.88, 10.55, 10.70, "urbain_principal"),  # Sousse
]


def resolve_road_type(lat: float, lon: float) -> str:
    for min_lat, max_lat, min_lon, max_lon, road_type in _CITY_BBOXES:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return road_type
    return "rural"


def normalize_road_type(road_type: str | None, lat: float, lon: float) -> str:
    if road_type and road_type in config.ROAD_TYPES:
        return road_type
    return resolve_road_type(lat, lon)

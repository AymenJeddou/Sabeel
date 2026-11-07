"""Rain-aware priority (feature): Open-Meteo forecast, free and keyless.

Autumn rain is when Tunisian potholes appear and get dangerous: water hides
the hole and soaks the base layer. Once a day (and from the dashboard), the
forecast precipitation for the next 48 h is fetched per ~25 km cell and stored
on each open pothole (`rain_mm_48h`). Priority adds +10 points to severity ≥ 3
potholes when ≥ RAIN_ALERT_MM is forecast, and the dashboard shows an alert.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db_models import Pothole
from backend.app.status import OPEN_STATUSES

logger = logging.getLogger(__name__)
_cache: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
TTL_S = 3600


def cell(lat: float, lon: float) -> tuple[float, float]:
    return round(lat * 4) / 4, round(lon * 4) / 4  # 0.25° ≈ 25 km


def rain_next_48h(forecast: dict[str, Any]) -> float:
    """Sum of the first two daily precipitation values (today + tomorrow)."""
    values = (forecast.get("daily") or {}).get("precipitation_sum") or []
    return round(sum(v or 0 for v in values[:2]), 1)


async def forecast(lat: float, lon: float) -> dict[str, Any] | None:
    key = cell(lat, lon)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < TTL_S:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                settings.open_meteo_url,
                params={"latitude": key[0], "longitude": key[1], "daily": "precipitation_sum,precipitation_probability_max",
                        "forecast_days": 3, "timezone": "UTC"},
            )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:  # noqa: BLE001 - weather is a bonus, never an error
        logger.info("Open-Meteo unavailable: %s", exc)
        return None
    _cache[key] = (time.monotonic(), data)
    return data


async def refresh(db: AsyncSession) -> dict[str, int]:
    """Stores rain_mm_48h on every open pothole and recomputes priority."""
    from backend.app.potholes import recompute_priority

    potholes = list((await db.execute(select(Pothole).where(Pothole.status.in_([s.value for s in OPEN_STATUSES])))).scalars())
    cells: dict[tuple[float, float], float | None] = {}
    for p in potholes:
        k = cell(p.lat, p.lon)
        if k not in cells:
            data = await forecast(p.lat, p.lon)
            cells[k] = rain_next_48h(data) if data else None
        if cells[k] is not None:
            p.rain_mm_48h = cells[k]
            recompute_priority(p)
    at_risk = sum(1 for p in potholes if (p.rain_mm_48h or 0) >= settings.rain_alert_mm and (p.severity or 0) >= 3)
    return {"potholes": len(potholes), "cells": len(cells), "at_risk": at_risk}

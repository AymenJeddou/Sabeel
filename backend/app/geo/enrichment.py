"""GPS point -> road, region and responsible office (issue #24).

- One Nominatim reverse-geocoding call (zoom 17 = nearest street) gives the
  road (`category=highway`, `type` = the OSM highway tag, `namedetails.ref`
  = RN1 / RR21 ...), the governorate (`address.state`) and the municipality.
  (The roadmap planned an Overpass query too; Nominatim already returns the
  nearest way with its tags, so one call is enough, and the public Overpass
  servers refuse requests from some networks.)
- Cache: `geo_cache`, keyed by coordinates rounded to ~30 m, so a place is
  never looked up twice. Nominatim's policy (real User-Agent, max 1 request/s)
  is respected by a process-wide lock.
- Failure: never raises. Without OSM, falls back to the Sprint 1 city-box
  heuristic plus the nearest seeded office, and records `source = "fallback"`.

Routing: national/regional roads -> the DGPC regional directorate of the
governorate; city streets -> the municipality; anything unresolved -> the
nearest municipality office (within 20 km) or the regional directorate.
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db_models import GeoCache, Office, Pothole
from backend.app.geo.road_class_map import classify, office_kind_for

logger = logging.getLogger(__name__)

_nominatim_lock = asyncio.Lock()
_last_nominatim = 0.0

# Sprint 1 heuristic, kept as the offline fallback: (min_lat, max_lat, min_lon, max_lon).
_CITY_BOXES = [(36.72, 36.90, 10.05, 10.35), (34.65, 34.80, 10.65, 10.85), (35.78, 35.88, 10.55, 10.70)]


def cache_key(lat: float, lon: float) -> str:
    return f"{round(lat / 0.0003)}:{round(lon / 0.0003)}"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def normalize_region(state: str | None) -> str | None:
    if not state:
        return None
    s = re.sub(r"^(Gouvernorat|Governorate|ولاية)\s+(de\s+|du\s+|d'|of\s+)?", "", state.strip(), flags=re.I)
    return s.strip() or None


def parse(nominatim: dict | None, lat: float, lon: float) -> dict[str, Any]:
    """Pure: a raw Nominatim answer -> enrichment fields. Used by tests with fixtures."""
    nominatim = nominatim if nominatim and "error" not in nominatim else None
    address = (nominatim or {}).get("address", {})
    municipality = address.get("city") or address.get("town") or address.get("municipality") or address.get("village")
    urban = bool(address.get("city") or address.get("town") or address.get("village") or address.get("suburb")
                 or address.get("city_district"))
    if not nominatim:
        urban = any(a <= lat <= b and c <= lon <= d for a, b, c, d in _CITY_BOXES)
    is_road = (nominatim or {}).get("category", (nominatim or {}).get("class")) == "highway"
    names = (nominatim or {}).get("namedetails") or {}
    ref = names.get("ref") if is_road else None
    road_class, road_type = classify((nominatim or {}).get("type") if is_road else None, ref, urban)
    road_name = names.get("name:fr") or (nominatim or {}).get("name") or address.get("road")
    district = address.get("suburb") or address.get("quarter") or address.get("city_district") or municipality
    label = ", ".join(p for p in (road_name, district) if p) or None
    return {
        "road_type": road_type,
        "road_class": road_class,
        "road_name": road_name,
        "road_ref": ref,
        "region": normalize_region(address.get("state")),
        "municipality": municipality,
        "address_label": label,
        "source": "osm" if nominatim else "fallback",
    }


async def _nominatim(client: httpx.AsyncClient, lat: float, lon: float) -> dict | None:
    global _last_nominatim
    async with _nominatim_lock:
        wait = 1.0 - (time.monotonic() - _last_nominatim)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            r = await client.get(
                f"{settings.nominatim_url}/reverse",
                params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 17, "addressdetails": 1, "namedetails": 1,
                        "accept-language": "fr"},
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:  # noqa: BLE001
            logger.info("Nominatim lookup failed: %s", exc)
            return None
        finally:
            _last_nominatim = time.monotonic()


async def lookup(db: AsyncSession, lat: float, lon: float) -> dict[str, Any]:
    """Cached OSM lookup. Never raises; a fallback result is not cached, so a
    later job can still get the real answer once OSM is reachable."""
    key = cache_key(lat, lon)
    cached = await db.get(GeoCache, key)
    if cached:
        return cached.data
    nominatim = None
    if settings.osm_enabled:
        async with httpx.AsyncClient(timeout=settings.osm_timeout_s, headers={"User-Agent": settings.osm_user_agent}) as client:
            nominatim = await _nominatim(client, lat, lon)
    data = parse(nominatim, lat, lon)
    if data["source"] == "osm":
        db.add(GeoCache(key=key, data=data))
    return data


async def route_office(db: AsyncSession, data: dict[str, Any], lat: float, lon: float) -> Office | None:
    offices = list((await db.execute(select(Office))).scalars())
    if not offices:
        return None
    kind = office_kind_for(data["road_class"])

    def norm(s: str | None) -> str:
        return re.sub(r"[^a-z]", "", (s or "").lower().replace("é", "e").replace("è", "e"))

    def nearest(candidates: list[Office], max_km: float = 1e9) -> Office | None:
        located = [o for o in candidates if o.lat is not None and o.lon is not None]
        located.sort(key=lambda o: haversine_m(lat, lon, o.lat, o.lon))
        return located[0] if located and haversine_m(lat, lon, located[0].lat, located[0].lon) <= max_km * 1000 else None

    by_kind = {k: [o for o in offices if o.kind == k] for k in ("Municipality", "DGPC", "Ministry of Equipment")}
    if kind == "Ministry of Equipment":
        return (by_kind["Ministry of Equipment"] or [None])[0]
    if kind == "DGPC":
        same_region = [o for o in by_kind["DGPC"] if data["region"] and norm(o.region) == norm(data["region"])]
        return (same_region or [None])[0] or nearest(by_kind["DGPC"])
    named = [o for o in by_kind["Municipality"] if data["municipality"] and norm(o.municipality) == norm(data["municipality"])]
    if named:
        return named[0]
    return (
        nearest(by_kind["Municipality"], max_km=20)
        or nearest(by_kind["DGPC"])
        or next((o for o in offices if o.code == settings.default_office_code), None)
    )


async def enrich_pothole(db: AsyncSession, p: Pothole) -> dict[str, Any]:
    """Writes road/region/office onto the pothole and logs the event."""
    from backend.app.potholes import record_event, recompute_priority

    data = await lookup(db, p.lat, p.lon)
    for field in ("road_type", "road_class", "road_name", "road_ref", "region", "municipality", "address_label"):
        setattr(p, field, data[field] or getattr(p, field))
    p.enrichment_source = data["source"]
    office = await route_office(db, data, p.lat, p.lon)
    if office and p.escalated_at is None:
        p.target_office_id = office.office_id
    if office:
        p.region = p.region or office.region
        p.municipality = p.municipality or office.municipality
    recompute_priority(p)
    await record_event(db, p, "system", "enriched", data={**data, "office": office.code if office else None})
    return data

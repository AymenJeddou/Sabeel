"""Derived fields and statistics for the authorities dashboard and its assistant.

Everything is computed in Python over the report rows. # ponytail: fine for
thousands of reports; move the aggregates into SQL if the table gets large.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import median

from backend.app.db_models import Report
from backend.app.status import ReportStatus

# Repair deadline by severity, in days. 48h for a 5 comes from the RAG rule
# PH-URB-PRIN-001; the others are MVP defaults to be confirmed with the city.
SLA_DAYS = {5: 2, 4: 7, 3: 14, 2: 30, 1: 30}
OPEN = (ReportStatus.NEW, ReportStatus.CONFIRMED, ReportStatus.SHEET_SENT)


def reference(device_report_id: str) -> str:
    """Same short code the mobile app shows (QueuedReport.reference)."""
    return "TN-" + re.sub("[^0-9a-zA-Z]", "", device_report_id)[:4].upper()


def summarize(report: Report, cluster_size: int, now: datetime) -> dict:
    due_at = None
    if report.score:
        due_at = report.created_at + timedelta(days=SLA_DAYS[report.score])
    is_open = report.status in OPEN
    overdue = bool(is_open and due_at and due_at < now)
    age_days = (now - report.created_at).days
    priority = (
        (report.score or 1) * 20 + min(cluster_size - 1, 5) * 8 + min(age_days, 30) + (15 if overdue else 0)
        if is_open
        else 0
    )
    return {
        "report_id": report.report_id,
        "ref": reference(report.device_report_id),
        "device_report_id": report.device_report_id,
        "device_id": report.device_id,
        "lat": report.lat,
        "lon": report.lon,
        "address": report.address,
        "score": report.score,
        "confidence": report.confidence,
        "status": report.status,
        "source": report.source,
        "cluster_id": report.cluster_id,
        "cluster_size": cluster_size,
        "target_office": report.target_office,
        "sheet_text": report.sheet_text,
        "photo_url": report.photo_url,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "due_at": due_at,
        "overdue": overdue,
        "priority": priority,
    }


def summarize_all(reports: list[Report]) -> list[dict]:
    now = datetime.now(timezone.utc)
    sizes = Counter(r.cluster_id for r in reports if r.cluster_id)
    return [summarize(r, sizes.get(r.cluster_id, 1) if r.cluster_id else 1, now) for r in reports]


def latest_per_pothole(summaries: list[dict]) -> list[dict]:
    """One row per physical pothole: the newest report of each cluster."""
    seen: dict = {}
    for s in sorted(summaries, key=lambda s: s["created_at"], reverse=True):
        seen.setdefault(s["cluster_id"] or s["report_id"], s)
    return list(seen.values())


def zone(address: str | None) -> str:
    """District part of an address ("Rue X, Lafayette" -> "Lafayette")."""
    return address.rsplit(",", 1)[-1].strip() if address and "," in address else "Non localisé"


def compute_stats(summaries: list[dict], weeks: int = 10) -> dict:
    potholes = latest_per_pothole(summaries)
    open_ = [p for p in potholes if p["status"] in OPEN]
    fixed = [p for p in potholes if p["status"] == ReportStatus.FIXED]
    repair_days = [(p["updated_at"] - p["created_at"]).total_seconds() / 86400 for p in fixed]

    now = datetime.now(timezone.utc)
    week0 = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    starts = [week0 - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]

    def week_of(dt: datetime) -> int | None:
        for i in range(len(starts) - 1, -1, -1):
            if dt >= starts[i]:
                return i
        return None

    reported, repaired = [0] * weeks, [0] * weeks
    for s in summaries:
        i = week_of(s["created_at"])
        if i is not None:
            reported[i] += 1
    for p in fixed:
        i = week_of(p["updated_at"])
        if i is not None:
            repaired[i] += 1

    return {
        "reports_total": len(summaries),
        "potholes_total": len(potholes),
        "open": len(open_),
        "urgent_open": sum(1 for p in open_ if (p["score"] or 0) >= 4),
        "overdue": sum(1 for p in open_ if p["overdue"]),
        "fixed": len(fixed),
        "rejected": sum(1 for p in potholes if p["status"] == ReportStatus.REJECTED),
        "median_repair_days": round(median(repair_days), 1) if repair_days else None,
        "by_status": dict(Counter(p["status"].value for p in potholes)),
        "by_severity": {str(k): v for k, v in Counter(p["score"] or 0 for p in open_).items()},
        "by_office": dict(Counter(p["target_office"] or "Non attribué" for p in open_)),
        "top_zones": Counter(zone(p["address"]) for p in open_).most_common(6),
        "weekly": [
            {"week": s.date().isoformat(), "reported": r, "fixed": f}
            for s, r, f in zip(starts, reported, repaired)
        ],
    }


async def reverse_geocode(lat: float, lon: float) -> str | None:
    """"Street, District" from OpenStreetMap Nominatim, or None on any failure.
    # ponytail: public Nominatim (1 req/s policy) is fine for the pilot; self-host
    # or cache by rounded coordinates if report volume grows."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=4, headers={"User-Agent": "Sabeel/0.1 (PFE pothole reporting)"}) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lon, "format": "json", "zoom": 17, "accept-language": "fr"},
            )
        a = r.json().get("address", {})
        street = a.get("road") or a.get("pedestrian")
        district = a.get("suburb") or a.get("quarter") or a.get("city_district") or a.get("town") or a.get("city")
        return ", ".join(p for p in (street, district) if p) or None
    except Exception:  # noqa: BLE001 - an address is a nicety, never a reason to fail a report
        return None

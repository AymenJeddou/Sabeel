"""Aggregates for the officer analytics view, the assistant and the public
page (issues #29, #30). Pure functions over pothole rows: easy to test with
hand-computed values.

# ponytail: computed in Python over the scoped rows (fine up to tens of
# thousands of potholes); move to SQL views if the table outgrows that.

Road health index (feature): per street, 100 minus 4 points per unit of open
severity on it, floored at 0. A street with no open pothole scores 100; five
open severity-5 potholes bring it to 0. Simple enough to explain to a mayor.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median, quantiles
from typing import Any, Callable, Iterable

from backend.app import sla
from backend.app.db_models import Pothole
from backend.app.status import OPEN_STATUSES

OPEN = {s.value for s in OPEN_STATUSES}


def _days(a: datetime | None, b: datetime | None) -> float | None:
    return (b - a).total_seconds() / 86400 if a and b else None


def med_p90(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"median": None, "p90": None, "n": 0}
    p90 = quantiles(values, n=10, method="inclusive")[-1] if len(values) > 1 else values[0]
    return {"median": round(median(values), 1), "p90": round(p90, 1), "n": len(values)}


def days_to_fix(potholes: Iterable[Pothole]) -> list[float]:
    return [d for p in potholes if p.status == "fixed" and (d := _days(p.created_at, p.fixed_at)) is not None]


def summary(potholes: list[Pothole], now: datetime, fp_rate: float | None = None) -> dict[str, Any]:
    open_ = [p for p in potholes if p.status in OPEN]
    levels = Counter(sla.level(p.confirmed_at, p.sla_due_at, now, True) for p in open_)
    with_deadline = sum(v for k, v in levels.items() if k)
    approval_hours = [
        (p.sheet_approved_at - p.sheet_generated_at).total_seconds() / 3600
        for p in potholes if p.sheet_approved_at and p.sheet_generated_at
    ]
    statuses = Counter(p.status for p in potholes)
    return {
        "potholes_total": len(potholes),
        "reports_total": sum(p.report_count for p in potholes),
        "by_status": dict(statuses),
        "open": len(open_),
        "new": statuses.get("new", 0),
        "confirmed": statuses.get("confirmed", 0),
        "sheet_sent": statuses.get("sheet_sent", 0),
        "fixed": statuses.get("fixed", 0),
        "rejected": statuses.get("rejected", 0),
        "reopened": statuses.get("reopened", 0),
        "urgent_open": sum(1 for p in open_ if (p.severity or 0) >= 4),
        "needs_review": sum(1 for p in open_ if p.needs_review),
        "overdue": levels.get("overdue", 0),
        "warning": levels.get("warning", 0),
        "overdue_rate": round(levels.get("overdue", 0) / with_deadline, 3) if with_deadline else None,
        "escalated": sum(1 for p in potholes if p.escalated_at),
        "rain_at_risk": sum(1 for p in open_ if p.priority_components and p.priority_components.get("rain")),
        "time_to_fix_days": med_p90(days_to_fix(potholes)),
        "sheet_approval_hours": med_p90(approval_hours),
        "fix_verified": sum(1 for p in potholes if p.status == "fixed" and p.fix_verified),
        "false_positive_rate": fp_rate,
        "by_severity": {str(k): v for k, v in sorted(Counter(p.severity or 0 for p in open_).items())},
    }


def time_to_fix(potholes: list[Pothole], key: Callable[[Pothole], str | None]) -> list[dict[str, Any]]:
    groups: dict[str, list[float]] = defaultdict(list)
    open_counts: Counter = Counter()
    for p in potholes:
        k = key(p) or "Non renseigné"
        if p.status == "fixed" and (d := _days(p.created_at, p.fixed_at)) is not None:
            groups[k].append(d)
        elif p.status in OPEN:
            open_counts[k] += 1
            groups.setdefault(k, [])
    return sorted(
        ({"key": k, **med_p90(v), "open": open_counts[k]} for k, v in groups.items()),
        key=lambda g: (g["median"] is None, -(g["median"] or 0)),
    )


def road_health(open_severity: float) -> int:
    return max(0, round(100 - 4 * open_severity))


def hotspots(potholes: list[Pothole], top: int = 10) -> dict[str, Any]:
    roads: dict[str, dict[str, Any]] = {}
    for p in potholes:
        if p.status not in OPEN:
            continue
        name = " ".join(x for x in (p.road_ref, p.road_name) if x) or p.address_label or "Voie non identifiée"
        r = roads.setdefault(name, {"road": name, "municipality": p.municipality, "open": 0, "severity_sum": 0, "max_severity": 0})
        r["open"] += 1
        r["severity_sum"] += p.severity or 1
        r["max_severity"] = max(r["max_severity"], p.severity or 1)
    ranked = sorted(roads.values(), key=lambda r: -r["severity_sum"])
    for r in ranked:
        r["health"] = road_health(r["severity_sum"])
    return {
        "roads": ranked[:top],
        "points": [[p.lat, p.lon, (p.severity or 1) / 5] for p in potholes if p.status in OPEN],
    }


def week_start(dt: datetime) -> datetime:
    return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def trend(potholes: list[Pothole], now: datetime, weeks: int = 12) -> list[dict[str, Any]]:
    first = week_start(now) - timedelta(weeks=weeks - 1)
    buckets = {first + timedelta(weeks=i): {"reported": 0, "confirmed": 0, "fixed": 0} for i in range(weeks)}
    for p in potholes:
        for field, when in (("reported", p.created_at), ("confirmed", p.confirmed_at), ("fixed", p.fixed_at)):
            if when and when >= first:
                buckets[week_start(when)][field] += 1
    return [{"week": k.date().isoformat(), **v} for k, v in buckets.items()]


def monthly(potholes: list[Pothole], now: datetime, months: int = 12) -> list[dict[str, Any]]:
    keys = []
    y, m = now.year, now.month
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    out = {k: {"reported": 0, "fixed": 0} for k in reversed(keys)}
    for p in potholes:
        for field, when in (("reported", p.created_at), ("fixed", p.fixed_at)):
            if when and (k := f"{when.year:04d}-{when.month:02d}") in out:
                out[k][field] += 1
    return [{"month": k, **v} for k, v in out.items()]


MIN_REGION_SIZE = 5


def public_stats(potholes: list[Pothole], now: datetime) -> dict[str, Any]:
    """Aggregate-only: no ids, no photos, no device data. Regions with fewer
    than MIN_REGION_SIZE potholes are suppressed (small counts can identify)."""
    visible = [p for p in potholes if p.status != "rejected"]
    fixed = [p for p in visible if p.status == "fixed"]
    regions: dict[str, list[Pothole]] = defaultdict(list)
    for p in visible:
        regions[p.region or "Autre"].append(p)
    region_rows = []
    for name, rows in sorted(regions.items(), key=lambda kv: -len(kv[1])):
        if len(rows) < MIN_REGION_SIZE:
            region_rows.append({"region": name, "suppressed": True, "reported": None, "fixed": None, "median_days_to_fix": None})
            continue
        region_rows.append({
            "region": name,
            "suppressed": False,
            "reported": len(rows),
            "fixed": sum(1 for p in rows if p.status == "fixed"),
            "median_days_to_fix": med_p90(days_to_fix(rows))["median"],
        })
    healthiest = hotspots(visible, top=1000)["roads"]
    return {
        "reported": len(visible),
        "confirmed": sum(1 for p in visible if p.confirmed_at),
        "open": sum(1 for p in visible if p.status in OPEN),
        "fixed": len(fixed),
        "fixed_last_7_days": sum(1 for p in fixed if p.fixed_at and p.fixed_at >= now - timedelta(days=7)),
        "fixed_last_30_days": sum(1 for p in fixed if p.fixed_at and p.fixed_at >= now - timedelta(days=30)),
        "fix_verified": sum(1 for p in fixed if p.fix_verified),
        "citizens_confirmations": sum(p.confirm_count for p in visible),
        "median_days_to_fix": med_p90(days_to_fix(visible))["median"],
        "regions": region_rows,
        "monthly": monthly(visible, now),
        "worst_roads": [{k: r[k] for k in ("road", "municipality", "open", "health")} for r in healthiest[:5]],
        "generated_at": now,
    }

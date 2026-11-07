"""Priority score: which pothole an office should fix first (issue #23).

The score is a plain **sum of named points**, so the dashboard can show exactly
why a pothole ranks where it does and `sum(components) == score` always holds.
(The roadmap sketched a product of weights; a sum is easier to explain to an
officer and keeps the same ordering on the cases in the acceptance criteria.)

| Component     | Points | Rule |
|---------------|--------|------|
| severity      | 0-50   | 10 × severity (1-5) |
| road          | 0-20   | importance of the road class |
| confirmations | 0-10   | 2.5 per distinct citizen beyond the first, capped |
| age           | 0-15   | 0.5 per day open, capped at 30 days |
| overdue       | 0 / 10 | SLA deadline passed |
| reopened      | 0 / 10 | citizens said a "fixed" pothole is still there |
| rain          | 0 / 10 | ≥ RAIN_ALERT_MM forecast in 48 h on a severity ≥ 3 pothole (water hides holes and widens them) |

Maximum 125. Closed potholes (fixed, rejected) score 0.
"""
from __future__ import annotations

from datetime import datetime

ROAD_POINTS = {
    "national": 20,
    "regional": 17,
    "urbain_principal": 15,
    "local": 14,
    "urbain_secondaire": 11,
    "rural": 10,
    "piste": 6,
    "autoroute": 20,
}
DEFAULT_ROAD_POINTS = 10  # until OSM enrichment has run


def compute(
    *,
    severity: int | None,
    road_class: str | None,
    device_count: int,
    opened_at: datetime,
    now: datetime,
    status: str,
    overdue: bool = False,
    rain_mm_48h: float | None = None,
    rain_alert_mm: float = 10,
) -> tuple[float, dict[str, float]]:
    """Returns (score, components). Pure: no database, no clock."""
    if status in ("fixed", "rejected"):
        return 0.0, {}
    sev = severity or 1
    days_open = max((now - opened_at).total_seconds() / 86400, 0)
    parts = {
        "severity": 10.0 * sev,
        "road": float(ROAD_POINTS.get(road_class or "", DEFAULT_ROAD_POINTS)),
        "confirmations": min(2.5 * max(device_count - 1, 0), 10.0),
        "age": round(min(0.5 * days_open, 15.0), 1),
        "overdue": 10.0 if overdue else 0.0,
        "reopened": 10.0 if status == "reopened" else 0.0,
        "rain": 10.0 if (rain_mm_48h or 0) >= rain_alert_mm and sev >= 3 else 0.0,
    }
    return round(sum(parts.values()), 1), parts

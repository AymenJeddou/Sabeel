"""Repair deadlines (issue #26). Policy is data, so non-developers can review it.

| Severity | Deadline after confirmation | Method (shown to officers and the assistant) |
|----------|-----------------------------|----------------------------------------------|
| 5        | 48 hours                    | immediate signage + permanent repair         |
| 4        | 7 days                      | immediate signage + permanent repair         |
| 3        | 14 days                     | hot-mix asphalt repair                       |
| 1-2      | none (monitor)              | cold patch at the next maintenance round     |

Levels: `warning` once 80 % of the time has elapsed, `overdue` at 100 %.
Escalation to the parent office happens once, when a pothole is overdue by
more than 100 % of its deadline (i.e. 2× the deadline has elapsed).

These values are MVP defaults (the 48 h rule mirrors the work-sheet playbook);
validate them with a municipal technical service before a real deployment.
"""
from __future__ import annotations

from datetime import datetime, timedelta

DEADLINES = {5: timedelta(hours=48), 4: timedelta(days=7), 3: timedelta(days=14)}
WARNING_AT = 0.8
ESCALATE_AT = 2.0

METHOD = {
    1: "surveillance, colmatage à l'enrobé à froid lors de la prochaine tournée",
    2: "surveillance, colmatage à l'enrobé à froid lors de la prochaine tournée",
    3: "réparation à l'enrobé à chaud sous 14 j : découpe à bords francs, nettoyage, couche d'accrochage, remplissage par couches, compactage",
    4: "balisage immédiat puis réparation définitive sous 7 j : découpe à la scie, purge, reprise de fondation si atteinte, enrobé à chaud compacté, joints scellés",
    5: "balisage immédiat (cônes, signalisation de nuit) puis réparation définitive sous 48 h : découpe à la scie, purge, reprise de fondation si atteinte, enrobé à chaud compacté, joints scellés",
}


def deadline_for(severity: int | None) -> timedelta | None:
    return DEADLINES.get(severity or 0)


def due_at(confirmed_at: datetime | None, severity: int | None) -> datetime | None:
    d = deadline_for(severity)
    return confirmed_at + d if confirmed_at and d else None


def level(confirmed_at: datetime | None, sla_due_at: datetime | None, now: datetime, is_open: bool) -> str | None:
    """None | 'ok' | 'warning' | 'overdue'."""
    if not (is_open and confirmed_at and sla_due_at):
        return None
    total = (sla_due_at - confirmed_at).total_seconds()
    elapsed = (now - confirmed_at).total_seconds()
    ratio = elapsed / total if total > 0 else 1
    return "overdue" if ratio >= 1 else "warning" if ratio >= WARNING_AT else "ok"


def overdue_by_hours(sla_due_at: datetime | None, now: datetime) -> float:
    return round(max((now - sla_due_at).total_seconds() / 3600, 0), 1) if sla_due_at else 0.0


def should_escalate(confirmed_at: datetime | None, sla_due_at: datetime | None, now: datetime) -> bool:
    if not (confirmed_at and sla_due_at):
        return False
    total = (sla_due_at - confirmed_at).total_seconds()
    return (now - confirmed_at).total_seconds() > ESCALATE_AT * total


def policy_markdown() -> str:
    return "\n".join(f"- Sévérité {s} : {METHOD[s]}" for s in (5, 4, 3, 2, 1))

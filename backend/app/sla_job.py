"""Daily SLA job (issue #26): recompute priorities (age, overdue) and escalate
potholes overdue by more than 100 % of their deadline to the parent office,
once per pothole."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import sla
from backend.app.db_models import Office, Pothole
from backend.app.potholes import now_utc, recompute_priority, record_event
from backend.app.status import OPEN_STATUSES


async def run_sla(db: AsyncSession, now: datetime | None = None) -> dict[str, int]:
    now = now or now_utc()
    offices = {o.office_id: o for o in (await db.execute(select(Office))).scalars()}
    open_ = list((await db.execute(select(Pothole).where(Pothole.status.in_([s.value for s in OPEN_STATUSES])))).scalars())
    escalated = 0
    for p in open_:
        recompute_priority(p, now)
        if p.escalated_at or not sla.should_escalate(p.confirmed_at, p.sla_due_at, now):
            continue
        current = offices.get(p.target_office_id)
        parent = offices.get(current.parent_office_id) if current and current.parent_office_id else None
        if parent is None:
            continue
        p.target_office_id = parent.office_id
        p.escalated_at = now
        p.updated_at = now
        await record_event(
            db, p, "system", "escalated",
            note=f"{current.name} → {parent.name}",
            data={"from": current.code, "to": parent.code, "overdue_by_hours": sla.overdue_by_hours(p.sla_due_at, now)},
        )
        escalated += 1
    return {"open": len(open_), "escalated": escalated}

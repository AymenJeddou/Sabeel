"""Scheduled maintenance (X-Internal-Token header = INTERNAL_TOKEN).

On Cloud Run the API scales to zero, so nothing runs between requests. The
GitHub Actions workflow `.github/workflows/scheduler.yml` calls
`POST /internal/run` every 10 minutes: it runs due jobs and, once a day,
the SLA escalation and the weather refresh.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import jobs, weather
from backend.app.auth import require_internal
from backend.app.db import get_db
from backend.app.sla_job import run_sla

router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal)], include_in_schema=False)


@router.post("/jobs/run")
async def run_jobs() -> dict:
    return {"jobs_run": await jobs.run_due()}


@router.post("/sla/run")
async def sla_run(db: AsyncSession = Depends(get_db)) -> dict:
    result = await run_sla(db)
    await db.commit()
    return result


@router.post("/weather/run")
async def weather_run(db: AsyncSession = Depends(get_db)) -> dict:
    result = await weather.refresh(db)
    await db.commit()
    return result


@router.post("/run")
async def run_all(daily: bool = False, db: AsyncSession = Depends(get_db)) -> dict:
    out: dict = {"jobs_run": await jobs.run_due()}
    if daily:
        out["sla"] = await run_sla(db)
        out["weather"] = await weather.refresh(db)
        await db.commit()
    return out

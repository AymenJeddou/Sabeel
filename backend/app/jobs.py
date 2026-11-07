"""Background jobs: OSM enrichment and RAG work sheets (issues #24, #25).

Why a table and not a queue service: zero cost, survives restarts, and is
visible to officers (a failed sheet shows a Retry button).

How the worker runs:
- right after a job is enqueued, a FastAPI background task calls `run_due()`;
- locally, an asyncio loop in the API process calls it every
  JOB_LOOP_INTERVAL_S seconds;
- on Cloud Run (CPU is throttled outside requests, instances scale to zero),
  set JOB_LOOP_INTERVAL_S=0 and let the GitHub Actions scheduler call
  `POST /internal/run` every 10 minutes (.github/workflows/scheduler.yml).

Retries back off 30 s, 2 min, 10 min, 1 h; after JOB_MAX_ATTEMPTS the job is
`failed`. Enrichment failures never block a sheet: the sheet job enriches with
fallback values itself if needed.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import rag_client
from backend.app.config import settings
from backend.app.db_models import Job, Pothole

logger = logging.getLogger(__name__)

BACKOFF = [timedelta(seconds=30), timedelta(minutes=2), timedelta(minutes=10), timedelta(hours=1)]
STALE_RUNNING = timedelta(minutes=10)


class JobError(Exception):
    """Raised by a handler to request a retry."""


async def enqueue(db: AsyncSession, pothole_id: uuid.UUID, job_type: str) -> None:
    """Adds a job unless one of the same type is already queued or running."""
    await db.execute(
        insert(Job)
        .values(pothole_id=pothole_id, type=job_type)
        .on_conflict_do_nothing(index_elements=["pothole_id", "type"], index_where=text("status IN ('queued', 'running')"))
    )


async def handle_enrich(db: AsyncSession, p: Pothole) -> None:
    from backend.app.geo.enrichment import enrich_pothole

    data = await enrich_pothole(db, p)
    if data["source"] == "fallback" and settings.osm_enabled:
        raise JobError("OpenStreetMap unreachable; fallback values stored, will retry")


async def handle_sheet(db: AsyncSession, p: Pothole) -> None:
    from backend.app.geo.enrichment import enrich_pothole
    from backend.app.potholes import now_utc, record_event

    if p.sheet_status not in ("queued", "failed"):
        return  # already generated or approved meanwhile
    if p.enrichment_source is None:
        await enrich_pothole(db, p)
    from backend.app.db_models import Office
    from backend.app.geo.road_class_map import office_kind_for

    office = await db.get(Office, p.target_office_id) if p.target_office_id else None
    result = await rag_client.generate(
        lat=p.lat, lon=p.lon, score=p.severity or 3, road_type=p.road_type,
        office_name=office.name if office else None, address=p.address_label,
        jurisdiction="municipal" if office_kind_for(p.road_class or "") == "Municipality" else "state",
    )
    if not result:
        raise JobError("RAG service unavailable")
    p.sheet_text = p.sheet_text_original = result["sheet_text"]
    p.sheet_citations = result.get("rule_citations") or []
    p.sheet_status = "generated"
    p.sheet_generated_at = now_utc()
    await record_event(
        db, p, "system", "sheet_generated",
        data={"road_type": result.get("road_type"), "generation_ms": result.get("generation_ms"),
              "citations": [c.get("rule_id") for c in p.sheet_citations]},
    )


HANDLERS = {"enrich": handle_enrich, "sheet": handle_sheet}


async def run_job(session_factory, job_id: int) -> str:
    """Runs one claimed job in its own transaction; returns its new status."""
    from backend.app.potholes import now_utc

    async with session_factory() as db:
        job = await db.get(Job, job_id)
        p = await db.get(Pothole, job.pothole_id)
        try:
            await HANDLERS[job.type](db, p)
            job.status, job.last_error = "done", None
        except Exception as exc:  # noqa: BLE001 - every failure becomes a retry
            if not isinstance(exc, JobError):
                # Unknown error: discard partial writes. A JobError keeps them
                # (e.g. the fallback enrichment values).
                await db.rollback()
                job = await db.get(Job, job_id)
                p = await db.get(Pothole, job.pothole_id)
            logger.warning("Job %s (%s) failed: %s", job.id, job.type, exc)
            job.last_error = str(exc)[:500]
            if job.attempts >= settings.job_max_attempts:
                job.status = "failed"
                if job.type == "sheet":
                    p.sheet_status = "failed"
            else:
                job.status = "queued"
                job.next_attempt_at = now_utc() + BACKOFF[min(job.attempts - 1, len(BACKOFF) - 1)]
        job.updated_at = now_utc()
        await db.commit()
        return job.status


async def claim(session_factory) -> int | None:
    from backend.app.potholes import now_utc

    async with session_factory() as db:
        job = await db.scalar(
            select(Job)
            .where(Job.status == "queued", Job.next_attempt_at <= now_utc())
            # Enrichment first: a sheet reads the road type it produces.
            .order_by(Job.type != "enrich", Job.next_attempt_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        job.status, job.attempts, job.updated_at = "running", job.attempts + 1, now_utc()
        await db.commit()
        return job.id


async def run_due(session_factory=None, max_jobs: int = 50) -> int:
    """Runs due jobs until none are left (or max_jobs); returns how many ran."""
    from backend.app.db import async_session
    from backend.app.potholes import now_utc

    session_factory = session_factory or async_session
    async with session_factory() as db:  # recover jobs from a crashed worker
        await db.execute(
            update(Job)
            .where(Job.status == "running", Job.updated_at < now_utc() - STALE_RUNNING)
            .values(status="queued")
        )
        await db.commit()
    ran = 0
    while ran < max_jobs:
        job_id = await claim(session_factory)
        if job_id is None:
            break
        await run_job(session_factory, job_id)
        ran += 1
    return ran


_running = asyncio.Lock()


async def kick() -> None:
    """Background-task entry point: one worker pass per process at a time."""
    if _running.locked():
        return
    async with _running:
        try:
            await run_due()
        except Exception:  # noqa: BLE001
            logger.exception("Job worker pass failed")


async def loop(interval_s: float) -> None:
    while True:
        await kick()
        await asyncio.sleep(interval_s)

"""Sabeel Core API.

Startup: applies database migrations, loads the ONNX model (so the first
citizen doesn't pay ~0.5 s), and starts the background job loop unless
JOB_LOOP_INTERVAL_S=0.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.app import jobs, storage
from backend.app.config import settings
from backend.app.db import engine
from backend.app.migrate import migrate
from backend.app.routers import assistant, authorities, internal, map, messages, potholes, public, reports
from backend.app.vision_client import warm_up

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sabeel")


@asynccontextmanager
async def lifespan(_: FastAPI):
    applied = await migrate(engine)
    if applied:
        logger.info("Applied migrations: %s", ", ".join(applied))
    await asyncio.to_thread(warm_up)
    loop_task = asyncio.create_task(jobs.loop(settings.job_loop_interval_s)) if settings.job_loop_interval_s > 0 else None
    yield
    if loop_task:
        loop_task.cancel()


app = FastAPI(
    title="Sabeel Core API",
    version="1.0.0",
    description="Pothole reporting and management for Tunisia. Officer routes need `Authorization: Bearer <office token>`.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Retry-After"],
)

storage.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(storage.STATIC_DIR)), name="static")

for module in (reports, potholes, map, authorities, public, messages, assistant, internal):
    app.include_router(module.router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}

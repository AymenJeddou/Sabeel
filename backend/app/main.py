from fastapi import FastAPI
from sqlalchemy import text

from backend.app.db import engine
from backend.app.routers import map as map_router
from backend.app.routers import reports as reports_router

app = FastAPI(title="RoadScan Core API", version="0.1.0")

app.include_router(reports_router.router)
app.include_router(map_router.router)


@app.get("/health")
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok"}

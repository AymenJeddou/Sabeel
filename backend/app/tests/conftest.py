"""Test setup: an isolated database, rebuilt from the migrations once per run
and truncated before every test (issue #12: tests no longer share the dev DB).

- TEST_DATABASE_URL (default: DATABASE_URL with the database name `sabeel_test`)
  is created if missing; its `public` schema is dropped and re-migrated.
- No network: OSM, the RAG service, Open-Meteo and OSRM are disabled or faked.
- Offices are seeded with demo tokens: `demo-<code>` (see seed_offices.py).

A bare `TestClient(app)` spins up a new event loop per request on Windows, while
pooled asyncpg connections stay bound to the loop that created them; using
TestClient as a context manager keeps one loop for the whole session.
"""
import asyncio
import io
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("JOB_LOOP_INTERVAL_S", "0")
os.environ.setdefault("OSM_ENABLED", "false")
os.environ.setdefault("BLUR_FACES_AND_PLATES", "true")
os.environ.setdefault("INTERNAL_TOKEN", "test-internal")

from sqlalchemy.engine import make_url  # noqa: E402

_base = make_url(os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/roadscan"))
TEST_URL = os.environ.get("TEST_DATABASE_URL") or _base.set(database="sabeel_test").render_as_string(hide_password=False)
os.environ["DATABASE_URL"] = TEST_URL

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SEED_DIR = Path(__file__).resolve().parents[1] / "static" / "photos" / "_seed"
POTHOLE_JPG = (SEED_DIR / "p08.jpg").read_bytes()  # the model finds a pothole here
ROAD_JPG = (SEED_DIR / "fp_crack.jpg").read_bytes()  # ... and nothing here


async def _reset_database() -> None:
    url = make_url(TEST_URL)
    dsn = f"postgresql://{url.username}:{url.password}@{url.host}:{url.port or 5432}"
    admin = await asyncpg.connect(f"{dsn}/postgres")
    try:
        if not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database):
            await admin.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await admin.close()
    conn = await asyncpg.connect(f"{dsn}/{url.database}")
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    finally:
        await conn.close()


asyncio.run(_reset_database())

from backend.app import rag_client, ratelimit  # noqa: E402
from backend.app.db import async_session  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.routers.public import clear_cache as clear_public_cache  # noqa: E402

TABLES = "report_events, confirmations, jobs, feedback_labels, geo_cache, messages, reports, potholes, offices"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db(client, monkeypatch):
    async def reset():
        from backend.app.scripts.seed_offices import upsert_offices

        async with async_session() as db:
            from sqlalchemy import text

            await db.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
            await upsert_offices(db, demo=True)
            await db.commit()

    client.portal.call(reset)
    ratelimit.reset()
    clear_public_cache()

    async def fake_generate(lat, lon, score, road_type=None, **_):
        return {
            "sheet_text": f"Fiche de travaux : nid-de-poule sévérité {score}/5.\nAction : réparation.\nRéférences: TN-CCL2018-ART69",
            "rule_citations": [{"rule_id": "TN-CCL2018-ART69", "source": "Loi 2018-29, art. 69", "excerpt": "domaine public communal"}],
            "target_office": "Municipality",
            "road_type": road_type or "urbain_principal",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_ms": 12.0,
        }

    async def no_chat(prompt):
        return None

    monkeypatch.setattr(rag_client, "generate", fake_generate)
    monkeypatch.setattr(rag_client, "chat", no_chat)
    yield


def auth(code: str = "mun-tunis") -> dict:
    return {"Authorization": f"Bearer demo-{code}"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def report_form(**overrides) -> dict:
    form = {
        "device_report_id": f"test-{uuid.uuid4()}",
        "device_id": f"device-{uuid.uuid4()}",
        "lat": "36.80650",
        "lon": "10.18150",
        "gps_accuracy_m": "4.2",
        "speed_kmh": "0",
        "direction_deg": "270.0",
        "captured_at": now_iso(),
        "source": "manual",
    }
    form.update({k: str(v) for k, v in overrides.items()})
    return form


def submit(client, photo: bytes = POTHOLE_JPG, **overrides):
    files = {"photo": ("pothole.jpg", io.BytesIO(photo), "image/jpeg")}
    return client.post("/reports", data=report_form(**overrides), files=files)


def run_jobs(client) -> int:
    from backend.app.jobs import run_due

    return client.portal.call(run_due)


def db_call(client, fn):
    """Runs `await fn(db)` in a fresh session on the app's loop and commits."""
    async def go():
        async with async_session() as db:
            out = await fn(db)
            await db.commit()
            return out

    return client.portal.call(go)

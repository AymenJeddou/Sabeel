"""Applies backend/app/db/migrations/NNN_*.sql in order, once each.

    python -m backend.app.migrate        (from the repo root)

The API also runs this on startup (main.py lifespan), so a fresh database or a
new Cloud Run revision is always up to date. Applied versions are recorded in
`schema_migrations`; a Postgres advisory lock stops two instances migrating at
the same time. Each file runs in its own transaction.

Rule: never edit a migration that has been merged; add a new numbered file.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

MIGRATIONS_DIR = Path(__file__).resolve().parent / "db" / "migrations"
_LOCK_ID = 727_001  # arbitrary, constant


async def migrate(engine: AsyncEngine) -> list[str]:
    """Returns the versions applied by this call (empty when up to date)."""
    applied_now: list[str] = []
    async with engine.connect() as sa_conn:
        raw = (await sa_conn.get_raw_connection()).driver_connection  # asyncpg: multi-statement scripts
        await raw.execute("SELECT pg_advisory_lock($1)", _LOCK_ID)
        try:
            await raw.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = {r["version"] for r in await raw.fetch("SELECT version FROM schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if path.stem in done:
                    continue
                async with raw.transaction():
                    await raw.execute(path.read_text(encoding="utf-8"))
                    await raw.execute("INSERT INTO schema_migrations (version) VALUES ($1)", path.stem)
                applied_now.append(path.stem)
        finally:
            await raw.execute("SELECT pg_advisory_unlock($1)", _LOCK_ID)
    return applied_now


if __name__ == "__main__":
    from backend.app.db import engine

    applied = asyncio.run(migrate(engine))
    print("Applied: " + ", ".join(applied) if applied else "Database is up to date.")

"""Creates the pilot offices and gives each one a fresh login token.

    python -m backend.app.scripts.seed_offices            # print new tokens
    python -m backend.app.scripts.seed_offices --demo     # fixed demo tokens

Tokens are printed once and stored only as SHA-256. Running it again rotates
every token. `--demo` uses predictable tokens (`demo-<code>`) so a jury can log
in to a local or staging demo; never use it on a real deployment.
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import hash_token, new_token
from backend.app.db_models import Office
from backend.app.scripts.offices_data import OFFICES


async def upsert_offices(db: AsyncSession, demo: bool = False, rotate: bool = True) -> dict[str, str]:
    """Creates missing offices, fixes their fields, and returns {code: token}
    for every office whose token was (re)set."""
    existing = {o.code: o for o in (await db.execute(select(Office))).scalars()}
    tokens: dict[str, str] = {}
    for code, name, kind, region, municipality, lat, lon, _parent in OFFICES:
        o = existing.get(code) or Office(code=code)
        o.name, o.kind, o.region, o.municipality, o.lat, o.lon = name, kind, region, municipality, lat, lon
        if rotate or o.token_hash is None:
            token = f"demo-{code}" if demo else new_token()
            o.token_hash = hash_token(token)
            tokens[code] = token
        db.add(o)
        existing[code] = o
    await db.flush()
    for code, *_rest, parent in OFFICES:
        existing[code].parent_office_id = existing[parent].office_id if parent else None
    await db.flush()
    return tokens


async def main(demo: bool) -> None:
    from backend.app.db import async_session, engine
    from backend.app.migrate import migrate

    await migrate(engine)
    async with async_session() as db:
        tokens = await upsert_offices(db, demo=demo)
        await db.commit()
    print("Office tokens (shown once; give each office its own):")
    for code, token in tokens.items():
        print(f"  {code:<18} {token}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--demo", action="store_true", help="use predictable demo-<code> tokens")
    asyncio.run(main(parser.parse_args().demo))

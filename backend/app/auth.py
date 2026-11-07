"""Officer authentication and scoping (issue #21).

An office logs in with `Authorization: Bearer <token>`: 32 random bytes,
stored only as SHA-256 (`offices.token_hash`). Tokens are created by
`python -m backend.app.scripts.seed_offices`, which prints each one once.

Scope: an office sees the potholes routed to it (`target_office_id`); the
ministry sees everything. Citizens never need a token.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db import get_db
from backend.app.db_models import Office, Pothole


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


async def optional_office(
    authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)
) -> Office | None:
    token = _bearer(authorization)
    if not token:
        return None
    office = await db.scalar(select(Office).where(Office.token_hash == hash_token(token)))
    if office is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid office token", {"WWW-Authenticate": "Bearer"})
    return office


async def require_office(office: Office | None = Depends(optional_office)) -> Office:
    if office is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Office token required", {"WWW-Authenticate": "Bearer"})
    return office


def can_see(office: Office, pothole: Pothole) -> bool:
    return office.is_ministry or pothole.target_office_id == office.office_id


def ensure_scope(office: Office, pothole: Pothole) -> None:
    if not can_see(office, pothole):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This pothole is routed to another office")


def scope_filter(office: Office):
    """SQLAlchemy WHERE clause limiting a potholes query to the office's scope."""
    return True if office.is_ministry else Pothole.target_office_id == office.office_id


def resolve_office_id(office: Office, office_id: str) -> uuid.UUID:
    """`/authorities/me/...` or the office's own id; the ministry may name any office."""
    if office_id == "me":
        return office.office_id
    try:
        wanted = uuid.UUID(office_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown office") from exc
    if wanted != office.office_id and not office.is_ministry:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only read your own office")
    return wanted


async def require_internal(x_internal_token: str | None = Header(default=None)) -> None:
    """Protects /internal/* (called by the scheduler). Disabled when INTERNAL_TOKEN is empty."""
    if not settings.internal_token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if not x_internal_token or not hmac.compare_digest(x_internal_token, settings.internal_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid internal token")

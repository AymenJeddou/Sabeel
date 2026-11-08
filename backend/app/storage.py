"""Photo storage: local disk for development, Supabase Storage in production.

Cloud Run's filesystem is wiped on every new instance, so deployed instances
must set STORAGE_BACKEND=supabase (free tier: 1 GB). Both backends return a
URL the apps can load directly; `delete()` accepts that same URL.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from backend.app.config import settings

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
PHOTOS_DIR = STATIC_DIR / "photos"


def _local(url: str, root: Path) -> Path | None:
    """The file a /static/... URL names, or None if it would leave `root` (../ tricks)."""
    path = (STATIC_DIR / url.removeprefix("/static/")).resolve()
    return path if path.is_relative_to(root.resolve()) else None


def _supabase_object(key: str) -> str:
    return f"{settings.supabase_url}/storage/v1/object/{settings.supabase_bucket}/{key}"


async def save(key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Stores `data` under photos/<key> and returns its public URL."""
    if settings.storage_backend == "supabase":
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                _supabase_object(key),
                content=data,
                headers={
                    "Authorization": f"Bearer {settings.supabase_service_key}",
                    "Content-Type": content_type,
                    "x-upsert": "true",
                },
            )
        r.raise_for_status()
        return f"{settings.supabase_url}/storage/v1/object/public/{settings.supabase_bucket}/{key}"
    path = PHOTOS_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"/static/photos/{key}"


async def delete(url: str | None) -> None:
    """Best effort: a failed delete is logged, never raised."""
    if not url or "/_seed/" in url:
        return
    try:
        if url.startswith("/static/photos/"):
            if path := _local(url, PHOTOS_DIR):
                path.unlink(missing_ok=True)
        elif settings.storage_backend == "supabase" and "/object/public/" in url:
            key = url.split(f"/object/public/{settings.supabase_bucket}/", 1)[1]
            async with httpx.AsyncClient(timeout=20) as client:
                await client.delete(
                    _supabase_object(key), headers={"Authorization": f"Bearer {settings.supabase_service_key}"}
                )
    except Exception:  # noqa: BLE001
        logger.warning("Could not delete photo %s", url, exc_info=True)


async def read(url: str) -> bytes | None:
    """Photo bytes for a stored URL (used to re-run the model on a photo)."""
    try:
        if url.startswith("/static/"):
            path = _local(url, STATIC_DIR)
            return path.read_bytes() if path else None
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
        r.raise_for_status()
        return r.content
    except Exception:  # noqa: BLE001
        return None

"""In-memory sliding-window rate limits (NFR-6, issue #21).

    Depends(limit("reports_device", 10, 60, by="device"))

Keys: the client IP, or the `device_id` form/query field, or the bearer
token. Exceeding a limit returns 429 with `Retry-After`.

# ponytail: limits are per API instance (a process-local dict). Fine for the
# pilot; move to Redis or Postgres if several instances must share one budget.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from backend.app.config import settings

_hits: dict[str, deque[float]] = defaultdict(deque)


def reset() -> None:
    _hits.clear()


def hit(key: str, max_calls: int, window_s: float, now: float | None = None) -> float | None:
    """Records one call; returns seconds to wait if over the limit, else None."""
    now = time.monotonic() if now is None else now
    q = _hits[key]
    while q and q[0] <= now - window_s:
        q.popleft()
    if len(q) >= max_calls:
        return max(q[0] + window_s - now, 1)
    q.append(now)
    return None


def _client_ip(request: Request) -> str:
    # Cloud Run puts the real client first in X-Forwarded-For.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def limit(name: str, max_calls: int, window_s: float, by: str = "ip"):
    async def dependency(request: Request) -> None:
        if not settings.rate_limits_enabled:
            return
        if by == "device":
            ident = request.query_params.get("device_id")
            if ident is None and request.headers.get("content-type", "").startswith(("multipart/", "application/x-www")):
                ident = (await request.form()).get("device_id")
            if ident is None and request.headers.get("content-type", "").startswith("application/json"):
                try:
                    ident = (await request.json()).get("device_id")
                except Exception:  # noqa: BLE001
                    ident = None
            ident = str(ident or _client_ip(request))
        elif by == "token":
            ident = request.headers.get("authorization", _client_ip(request))
        else:
            ident = _client_ip(request)
        wait = hit(f"{name}:{ident}", max_calls, window_s)
        if wait is not None:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Trop de requêtes, réessayez plus tard.",
                {"Retry-After": str(int(wait))},
            )

    return dependency

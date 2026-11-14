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


SWEEP_AT = 10_000  # keys kept before idle ones are dropped
MAX_WINDOW_S = 86_400  # longest window any route uses (confirm_device)


def reset() -> None:
    _hits.clear()


def _sweep(now: float) -> None:
    """Drops keys idle for longer than any window: every IP or device ever seen would
    otherwise stay in memory for the life of the process."""
    for key in [k for k, q in _hits.items() if not q or q[-1] <= now - MAX_WINDOW_S]:
        del _hits[key]


def hit(key: str, max_calls: int, window_s: float, now: float | None = None) -> float | None:
    """Records one call; returns seconds to wait if over the limit, else None."""
    now = time.monotonic() if now is None else now
    if len(_hits) > SWEEP_AT:
        _sweep(now)
    q = _hits[key]
    while q and q[0] <= now - window_s:
        q.popleft()
    if len(q) >= max_calls:
        return max(q[0] + window_s - now, 1)
    q.append(now)
    return None


def _client_ip(request: Request) -> str:
    # The proxy in front of us (Cloud Run, Hugging Face) appends the address it saw, so the
    # last entry is the real client; the first one is whatever the client chose to send.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "?")


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

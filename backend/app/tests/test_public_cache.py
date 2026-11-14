"""The public endpoints' response cache stays bounded."""
import asyncio

from backend.app.routers import public


def test_cache_never_grows_past_its_cap(monkeypatch):
    public.clear_cache()
    monkeypatch.setattr(public, "CACHE_MAX", 5)

    async def build():
        return []

    for i in range(20):
        asyncio.run(public._cached(f"map:{i}", build))
    assert len(public._cache) <= 5
    assert "map:19" in public._cache
    public.clear_cache()

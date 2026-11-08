"""Sliding-window limiter: pure, no database."""
from backend.app import ratelimit


def test_window_slides_and_reports_wait():
    ratelimit.reset()
    assert ratelimit.hit("k", 2, 60, now=0) is None
    assert ratelimit.hit("k", 2, 60, now=10) is None
    assert ratelimit.hit("k", 2, 60, now=20) == 40  # oldest call frees up at t=60
    assert ratelimit.hit("k", 2, 60, now=60.5) is None
    assert ratelimit.hit("other", 2, 60, now=20) is None  # keys are independent


def test_wait_is_at_least_one_second():
    ratelimit.reset()
    ratelimit.hit("k", 1, 60, now=0)
    assert ratelimit.hit("k", 1, 60, now=59.9) == 1


def test_client_ip_cannot_be_spoofed_with_x_forwarded_for():
    from starlette.requests import Request

    def req(fwd):
        headers = [(b"x-forwarded-for", fwd.encode())] if fwd else []
        return Request({"type": "http", "headers": headers, "client": ("10.0.0.9", 1)})

    assert ratelimit._client_ip(req("1.2.3.4, 41.226.0.7")) == "41.226.0.7"
    assert ratelimit._client_ip(req("41.226.0.7")) == "41.226.0.7"
    assert ratelimit._client_ip(req("")) == "10.0.0.9"


def test_idle_keys_are_swept(monkeypatch):
    ratelimit.reset()
    monkeypatch.setattr(ratelimit, "SWEEP_AT", 3)
    for i in range(4):
        ratelimit.hit(f"old{i}", 5, 60, now=0)
    ratelimit.hit("fresh", 5, 60, now=ratelimit.MAX_WINDOW_S + 1)
    assert set(ratelimit._hits) == {"fresh"}

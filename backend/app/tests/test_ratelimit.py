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

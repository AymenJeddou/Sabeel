"""State machine, priority formula and SLA maths: pure functions, no database."""
from datetime import datetime, timedelta, timezone

from backend.app import priority, sla
from backend.app.status import ReportStatus as S, is_valid_transition

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


def test_forward_chain_is_allowed():
    assert is_valid_transition(S.NEW, S.CONFIRMED)
    assert is_valid_transition(S.CONFIRMED, S.SHEET_SENT)
    assert is_valid_transition(S.SHEET_SENT, S.FIXED)
    assert is_valid_transition(S.FIXED, S.REOPENED)
    assert is_valid_transition(S.REOPENED, S.FIXED)


def test_skips_and_backwards_moves_are_rejected():
    assert not is_valid_transition(S.NEW, S.FIXED)  # cahier F4 acceptance 1
    assert not is_valid_transition(S.NEW, S.SHEET_SENT)
    assert not is_valid_transition(S.FIXED, S.CONFIRMED)
    assert not is_valid_transition(S.CONFIRMED, S.NEW)
    assert not is_valid_transition(S.NEW, S.REOPENED)


def test_small_potholes_can_be_fixed_without_a_sheet():
    assert not is_valid_transition(S.CONFIRMED, S.FIXED, sheet_required=True)
    assert is_valid_transition(S.CONFIRMED, S.FIXED, sheet_required=False)


def test_reject_only_from_open_states():
    for s in (S.NEW, S.CONFIRMED, S.SHEET_SENT, S.REOPENED):
        assert is_valid_transition(s, S.REJECTED)
    assert not is_valid_transition(S.FIXED, S.REJECTED)
    assert not is_valid_transition(S.REJECTED, S.CONFIRMED)


def _score(**kw):
    base = dict(severity=3, road_class="rural", device_count=2, opened_at=NOW, now=NOW, status="confirmed")
    return priority.compute(**{**base, **kw})


def test_priority_components_sum_to_the_score():
    score, parts = _score(severity=4, road_class="national", device_count=5, opened_at=NOW - timedelta(days=12),
                          overdue=True, rain_mm_48h=30, status="reopened")
    assert abs(sum(parts.values()) - score) < 1e-6
    assert set(parts) == {"severity", "road", "confirmations", "age", "overdue", "reopened", "rain"}


def test_severe_national_outranks_medium_rural():  # issue #23 acceptance
    assert _score(severity=5, road_class="national")[0] > _score(severity=3, road_class="rural")[0]


def test_closed_potholes_have_no_priority():
    assert _score(status="fixed") == (0.0, {})


def test_rain_boost_only_for_serious_potholes():
    assert _score(severity=3, rain_mm_48h=12)[1]["rain"] == 10
    assert _score(severity=2, rain_mm_48h=40)[1]["rain"] == 0
    assert _score(severity=5, rain_mm_48h=2)[1]["rain"] == 0


def test_sla_deadlines_and_levels():
    confirmed = NOW - timedelta(days=3)
    due = sla.due_at(confirmed, 5)
    assert due == confirmed + timedelta(hours=48)
    assert sla.level(confirmed, due, NOW, True) == "overdue"  # issue #26 acceptance 1
    assert sla.due_at(confirmed, 2) is None
    due4 = sla.due_at(NOW - timedelta(days=6), 4)
    assert sla.level(NOW - timedelta(days=6), due4, NOW, True) == "warning"  # 6/7 > 80 %
    assert sla.level(NOW - timedelta(days=1), sla.due_at(NOW - timedelta(days=1), 4), NOW, True) == "ok"
    assert sla.level(confirmed, due, NOW, False) is None


def test_escalation_after_twice_the_deadline():
    confirmed = NOW - timedelta(days=5)
    assert sla.should_escalate(confirmed, sla.due_at(confirmed, 5), NOW)  # 5 d > 2 x 48 h
    recent = NOW - timedelta(days=3)
    assert not sla.should_escalate(recent, sla.due_at(recent, 5), NOW)

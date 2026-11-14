"""Pure helpers of the weather and analytics modules. No database, no network."""
from datetime import datetime, timezone

from backend.app import analytics, weather


def test_forecast_cells_are_quarter_degrees():
    assert weather.cell(36.81, 10.18) == (36.75, 10.25)
    assert weather.cell(36.81, 10.18) == weather.cell(36.70, 10.20)  # same ~25 km cell
    assert weather.cell(-0.1, -0.13) == (0.0, -0.25)


def test_rain_is_today_plus_tomorrow():
    assert weather.rain_next_48h({"daily": {"precipitation_sum": [4.2, None, 30]}}) == 4.2
    assert weather.rain_next_48h({"daily": {"precipitation_sum": [4.25, 6]}}) == 10.2
    assert weather.rain_next_48h({}) == 0


def test_median_and_p90():
    assert analytics.med_p90([]) == {"median": None, "p90": None, "n": 0}
    assert analytics.med_p90([3.0]) == {"median": 3.0, "p90": 3.0, "n": 1}
    out = analytics.med_p90([float(d) for d in range(1, 11)])
    assert out == {"median": 5.5, "p90": 9.1, "n": 10}


def test_week_starts_on_monday_midnight():
    sunday = datetime(2026, 11, 8, 18, 30, tzinfo=timezone.utc)
    assert analytics.week_start(sunday) == datetime(2026, 11, 2, tzinfo=timezone.utc)


def _p(**kw):
    from types import SimpleNamespace

    base = dict(status="new", severity=3, road_ref=None, road_name=None, address_label=None,
                municipality="Tunis", lat=36.8, lon=10.18, created_at=None, fixed_at=None)
    return SimpleNamespace(**base | kw)


def test_monthly_buckets_cover_twelve_months_across_new_year():
    now = datetime(2026, 2, 10, tzinfo=timezone.utc)
    rows = [_p(created_at=datetime(2025, 12, 31, tzinfo=timezone.utc), fixed_at=datetime(2026, 2, 1, tzinfo=timezone.utc)),
            _p(created_at=datetime(2024, 1, 1, tzinfo=timezone.utc))]  # too old: ignored
    out = analytics.monthly(rows, now)
    assert len(out) == 12 and out[0]["month"] == "2025-03" and out[-1]["month"] == "2026-02"
    assert {m["month"]: m for m in out}["2025-12"]["reported"] == 1
    assert out[-1]["fixed"] == 1


def test_hotspots_rank_open_potholes_by_road():
    rows = [_p(road_ref="RN8", road_name="Route de Bizerte", severity=5),
            _p(road_ref="RN8", road_name="Route de Bizerte", severity=4),
            _p(road_name="Rue de Marseille", severity=2),
            _p(road_name="Rue de Marseille", severity=5, status="fixed"),  # closed: ignored
            _p(severity=None)]
    out = analytics.hotspots(rows)
    assert [r["road"] for r in out["roads"]] == ["RN8 Route de Bizerte", "Rue de Marseille", "Voie non identifiée"]
    assert out["roads"][0]["open"] == 2 and out["roads"][0]["max_severity"] == 5
    assert out["roads"][0]["health"] == analytics.road_health(9)
    assert len(out["points"]) == 4

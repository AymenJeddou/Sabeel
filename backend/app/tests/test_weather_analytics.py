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

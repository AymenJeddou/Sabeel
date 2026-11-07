"""Officer queue, export, analytics, SLA escalation, route planner, weather,
public transparency endpoints."""
import csv
import io
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from backend.app import analytics, routing, weather
from backend.app.db_models import Office, Pothole
from backend.app.sla_job import run_sla
from backend.app.tests.conftest import auth, db_call, run_jobs, submit

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


def two_potholes(client) -> tuple[str, str]:
    a = submit(client, device_id="phone-aaaaaaaa", lat=36.8065, lon=10.1815).json()["pothole_id"]
    submit(client, device_id="phone-bbbbbbbb", lat=36.8065, lon=10.1815)
    b = submit(client, device_id="phone-cccccccc", lat=36.8020, lon=10.1790).json()["pothole_id"]
    run_jobs(client)
    return a, b


def test_queue_sorted_by_priority_with_explanations(client):
    a, b = two_potholes(client)
    body = client.get("/authorities/me/queue", headers=auth()).json()
    items = body["items"]
    assert body["total"] == 2 and items[0]["pothole_id"] == a  # confirmed by 2 phones ranks higher
    assert items[0]["priority_score"] >= items[1]["priority_score"]
    assert abs(sum(items[0]["priority_components"].values()) - items[0]["priority_score"]) < 0.01
    only_new = client.get("/authorities/me/queue", params={"status": "new"}, headers=auth()).json()["items"]
    assert [i["pothole_id"] for i in only_new] == [b]
    page = client.get("/authorities/me/queue", params={"limit": 1}, headers=auth()).json()
    assert len(page["items"]) == 1 and page["next_cursor"] == 1


def test_other_office_ids_are_forbidden_except_for_the_ministry(client):
    tunis = db_call(client, lambda db: db.scalar(select(Office.office_id).where(Office.code == "mun-tunis")))
    assert client.get(f"/authorities/{tunis}/queue", headers=auth("mun-sfax")).status_code == 403
    assert client.get(f"/authorities/{tunis}/queue", headers=auth("ministry")).status_code == 200


def test_csv_and_geojson_exports_match_the_queue(client):
    two_potholes(client)
    queue = client.get("/authorities/me/queue", params={"status": "all"}, headers=auth()).json()["items"]
    raw = client.get("/export", params={"format": "csv"}, headers=auth()).content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(raw)))
    assert [r["pothole_id"] for r in rows] == [q["pothole_id"] for q in queue]
    geo = json.loads(client.get("/export", params={"format": "geojson"}, headers=auth()).content)
    assert geo["type"] == "FeatureCollection" and len(geo["features"]) == len(queue)
    lon, lat = geo["features"][0]["geometry"]["coordinates"]
    assert 10 < lon < 11 and 36 < lat < 37  # [lon, lat] order


def test_sla_job_escalates_once_to_the_parent_office(client):
    a, _ = two_potholes(client)
    db_call(client, lambda db: db.execute(update(Pothole).where(Pothole.pothole_id == a).values(
        severity=5, confirmed_at=NOW - timedelta(days=5), sla_due_at=NOW - timedelta(days=3))))
    first = db_call(client, lambda db: run_sla(db, NOW))
    second = db_call(client, lambda db: run_sla(db, NOW))
    assert (first["escalated"], second["escalated"]) == (1, 0)
    detail = client.get(f"/potholes/{a}", headers=auth("dre-tunis")).json()
    assert detail["target_office"].startswith("Direction Régionale") and detail["overdue"] is True
    assert any(e["kind"] == "escalated" for e in detail["events"])
    assert client.get(f"/potholes/{a}", headers=auth("mun-tunis")).json().get("events") is None  # no longer theirs


def test_internal_run_needs_the_token(client):
    assert client.post("/internal/run").status_code == 401
    assert client.post("/internal/run", headers={"X-Internal-Token": "test-internal"}).status_code == 200


def test_analytics_medians_and_scoping(client):
    class P:  # minimal stand-in for a Pothole row
        def __init__(self, days, status="fixed", region="Tunis"):
            self.status, self.region, self.created_at = status, region, NOW - timedelta(days=30)
            self.fixed_at = self.created_at + timedelta(days=days) if days is not None else None
            self.confirmed_at = self.sla_due_at = self.sheet_approved_at = self.sheet_generated_at = None
            self.severity, self.report_count, self.needs_review, self.escalated_at = 3, 1, False, None
            self.priority_components, self.fix_verified, self.municipality = {}, False, "Tunis"
            self.road_ref = self.road_name = self.address_label = None
            self.road_class, self.lat, self.lon, self.confirm_count = "rural", 36.8, 10.1, 0

    rows = [P(2), P(4), P(10), P(None, "confirmed")]
    s = analytics.summary(rows, NOW)
    assert s["time_to_fix_days"]["median"] == 4 and s["fixed"] == 3 and s["open"] == 1
    assert analytics.time_to_fix(rows, lambda p: p.region)[0]["median"] == 4
    assert analytics.road_health(5 * 5) == 0 and analytics.road_health(0) == 100

    two_potholes(client)
    assert client.get("/analytics/summary", headers=auth("mun-sfax")).json()["potholes_total"] == 0
    assert client.get("/analytics/summary", headers=auth("ministry")).json()["potholes_total"] == 2
    assert len(client.get("/analytics/trend", headers=auth()).json()) == 12
    assert client.get("/analytics/hotspots", headers=auth()).json()["roads"]


FORBIDDEN = {"device_id", "device_report_id", "photo_url", "sheet_text", "boxes", "fixed_proof_url", "reports", "events"}


def keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys(v)


def test_public_payloads_never_contain_private_fields(client):
    a, _ = two_potholes(client)
    for url in ("/public/stats", "/public/map", f"/public/potholes/{a}", "/map", f"/potholes/{a}"):
        body = client.get(url).json()
        assert not FORBIDDEN & set(keys(body)), url


def test_small_regions_are_suppressed_and_numbers_match_analytics(client):
    two_potholes(client)
    stats = client.get("/public/stats").json()
    assert stats["reported"] == 2 and all(r["suppressed"] for r in stats["regions"])  # fewer than 5
    summary = client.get("/analytics/summary", headers=auth("ministry")).json()
    assert stats["fixed"] == summary["fixed"] and stats["open"] == summary["open"]


def test_route_fallback_orders_stops_into_a_short_tour(client, monkeypatch):
    start = (36.80, 10.18)
    stops = [(36.83, 10.18), (36.81, 10.18), (36.82, 10.18)]
    assert routing.plan_fallback(start, stops) == [1, 2, 0]

    two_potholes(client)
    db_call(client, lambda db: db.execute(update(Pothole).values(status="confirmed")))
    monkeypatch.setattr("backend.app.config.settings.osrm_url", "http://127.0.0.1:9")  # unreachable
    body = client.get("/authorities/me/route", headers=auth()).json()
    assert body["engine"] == "fallback" and [s["stop"] for s in body["stops"]] == [1, 2]
    assert body["geometry"]["type"] == "LineString"


def test_weather_alert_and_rain_boost(client, monkeypatch):
    async def wet(lat, lon):
        return {"daily": {"time": ["2026-11-07", "2026-11-08", "2026-11-09"],
                          "precipitation_sum": [14.2, 6.0, 0.0], "precipitation_probability_max": [90, 70, 10]}}

    monkeypatch.setattr(weather, "forecast", wet)
    a, _ = two_potholes(client)
    db_call(client, lambda db: db.execute(update(Pothole).values(severity=4)))
    result = db_call(client, weather.refresh)
    assert result["at_risk"] == 2
    alert = client.get("/weather", headers=auth()).json()
    assert alert["alert"] is True and alert["rain_mm_48h"] == 20.2 and alert["at_risk"] == 2
    assert client.get(f"/potholes/{a}", headers=auth()).json()["priority_components"]["rain"] == 10

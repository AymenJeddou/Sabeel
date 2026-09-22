"""Integration tests against a real database -- run `docker compose up -d db` first.
Uses the shared `client` fixture from conftest.py.
"""
import io
import random
import uuid


def _random_point_in_bbox() -> tuple[str, str]:
    """(lat, lon) inside bbox 10.0,36.7,10.3,36.9, random so leftover rows from
    earlier runs don't dedup-merge it into an older cluster."""
    return f"{random.uniform(36.75, 36.85):.6f}", f"{random.uniform(10.05, 10.25):.6f}"


def _submit(client, lat: str, lon: str) -> str:
    files = {"photo": ("pothole.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")}
    form = {
        "device_report_id": f"test-map-{uuid.uuid4()}",
        "lat": lat,
        "lon": lon,
        "gps_accuracy_m": "4.2",
        "speed_kmh": "0",
        "direction_deg": "270.0",
        "captured_at": "2026-09-15T10:32:00Z",
        "source": "manual",
    }
    response = client.post("/reports", data=form, files=files)
    return response.json()["report_id"]


def test_get_map_returns_contract_shape(client):
    _submit(client, *_random_point_in_bbox())

    response = client.get("/map", params={"bbox": "10.0,36.7,10.3,36.9"})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    for item in body:
        assert set(item.keys()) == {"report_id", "lat", "lon", "score", "status", "cluster_id"}


def test_get_map_without_bbox_still_works(client):
    response = client.get("/map")
    assert response.status_code == 200


def test_get_map_bbox_excludes_reports_outside_it(client):
    inside_id = _submit(client, *_random_point_in_bbox())
    outside_id = _submit(client, lat="50.0", lon="50.0")  # far outside any Tunisia bbox

    response = client.get("/map", params={"bbox": "10.0,36.7,10.3,36.9"})

    assert response.status_code == 200
    ids = {item["report_id"] for item in response.json()}
    assert inside_id in ids
    assert outside_id not in ids


def test_get_map_invalid_bbox_returns_422(client):
    response = client.get("/map", params={"bbox": "not,a,valid,bbox"})
    assert response.status_code == 422

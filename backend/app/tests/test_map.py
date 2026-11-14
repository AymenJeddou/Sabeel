"""GET /map: one row per pothole, filters, bbox validation."""
from backend.app.tests.conftest import submit


def test_map_returns_one_row_per_pothole_with_contract_fields(client):
    submit(client, device_id="phone-aaaaaaaa", lat=36.8065, lon=10.1815)
    submit(client, device_id="phone-bbbbbbbb", lat=36.80651, lon=10.18151)
    rows = client.get("/map", params={"bbox": "10.0,36.7,10.3,36.9"}).json()
    assert len(rows) == 1
    assert {"pothole_id", "ref", "lat", "lon", "score", "status", "cluster_id", "report_count"} <= rows[0].keys()
    assert rows[0]["report_count"] == 2 and rows[0]["status"] == "confirmed"
    assert "device_id" not in rows[0] and "photo_url" not in rows[0]


def test_bbox_excludes_points_outside(client):
    inside = submit(client, lat=36.80, lon=10.18).json()["pothole_id"]
    outside = submit(client, lat=35.82, lon=10.63).json()["pothole_id"]  # Sousse
    ids = {r["pothole_id"] for r in client.get("/map", params={"bbox": "10.0,36.7,10.3,36.9"}).json()}
    assert inside in ids and outside not in ids


def test_severity_and_state_filters(client):
    pid = submit(client).json()["pothole_id"]
    sev = client.get("/map").json()[0]["score"]
    assert [r["pothole_id"] for r in client.get("/map", params={"sev": str(sev)}).json()] == [pid]
    assert client.get("/map", params={"sev": "1" if sev != 1 else "5"}).json() == []
    assert client.get("/map", params={"state": "fixed"}).json() == []
    assert len(client.get("/map", params={"state": "open"}).json()) == 1


def test_invalid_bbox_and_sev_return_422(client):
    assert client.get("/map", params={"bbox": "not,a,valid,bbox"}).status_code == 422
    assert client.get("/map", params={"bbox": "10.3,36.9,10.0,36.7"}).status_code == 422
    assert client.get("/map", params={"sev": "high"}).status_code == 422

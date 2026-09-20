from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_get_map_returns_contract_shape():
    response = client.get("/map", params={"bbox": "10.0,36.7,10.3,36.9"})

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) > 0
    for item in body:
        assert set(item.keys()) == {"report_id", "lat", "lon", "score", "status", "cluster_id"}


def test_get_map_without_bbox_still_works():
    response = client.get("/map")

    assert response.status_code == 200

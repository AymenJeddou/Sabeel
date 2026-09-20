import io

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _report_form():
    return {
        "device_report_id": "local-9f8e-test",
        "lat": "36.8065",
        "lon": "10.1815",
        "gps_accuracy_m": "4.2",
        "speed_kmh": "0",
        "direction_deg": "270.0",
        "captured_at": "2026-09-15T10:32:00Z",
        "source": "manual",
    }


def test_create_report_returns_contract_shape():
    files = {"photo": ("pothole.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")}
    response = client.post("/reports", data=_report_form(), files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["device_report_id"] == "local-9f8e-test"
    assert body["status"] == "new"
    assert body["score"] is None
    assert "report_id" in body


def test_get_report_by_device_id():
    response = client.get("/reports/local-9f8e-test")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"report_id", "status", "score"}


def test_patch_forward_transition_succeeds():
    # Sprint 1 stub treats every report as currently "confirmed".
    response = client.patch(
        f"/reports/{'11111111-1111-1111-1111-111111111111'}",
        json={"status": "sheet_sent"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sheet_sent"
    assert "updated_at" in body


def test_patch_backward_transition_returns_409():
    response = client.patch(
        f"/reports/{'11111111-1111-1111-1111-111111111111'}",
        json={"status": "new"},
    )

    assert response.status_code == 409


def test_patch_skip_transition_returns_409():
    response = client.patch(
        f"/reports/{'11111111-1111-1111-1111-111111111111'}",
        json={"status": "fixed"},
    )

    assert response.status_code == 409

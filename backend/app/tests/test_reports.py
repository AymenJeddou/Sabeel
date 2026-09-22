"""Integration tests against a real database -- run `docker compose up -d db`
first (see backend/app/README.md). Each test uses a fresh device_report_id
(device_report_id is UNIQUE) so repeated runs don't collide.
"""
import io
import uuid

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _report_form(device_report_id: str | None = None, **overrides):
    form = {
        "device_report_id": device_report_id or f"test-{uuid.uuid4()}",
        "lat": "36.8065",
        "lon": "10.1815",
        "gps_accuracy_m": "4.2",
        "speed_kmh": "0",
        "direction_deg": "270.0",
        "captured_at": "2026-09-15T10:32:00Z",
        "source": "manual",
    }
    form.update(overrides)
    return form


def _submit(device_report_id: str | None = None, **overrides):
    files = {"photo": ("pothole.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")}
    return client.post("/reports", data=_report_form(device_report_id, **overrides), files=files)


def test_create_report_returns_contract_shape():
    response = _submit()

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    # A fake JPEG payload can't score >= 1 from the real vision model.
    assert body["score"] is None
    assert "report_id" in body


def test_second_report_within_5m_is_deduplicated_and_confirmed():
    _submit(lat="36.80650", lon="10.18150")
    response = _submit(lat="36.80651", lon="10.18151")  # ~1.3m away

    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"


def test_get_report_by_device_id_returns_what_was_created():
    device_id = f"test-{uuid.uuid4()}"
    _submit(device_id)

    response = client.get(f"/reports/{device_id}")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"report_id", "status", "score"}


def test_get_report_unknown_device_id_returns_404():
    response = client.get(f"/reports/does-not-exist-{uuid.uuid4()}")
    assert response.status_code == 404


def test_patch_forward_transition_succeeds():
    create_response = _submit()
    report_id = create_response.json()["report_id"]

    response = client.patch(f"/reports/{report_id}", json={"status": "confirmed"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert "updated_at" in body


def test_patch_backward_transition_returns_409():
    create_response = _submit()
    report_id = create_response.json()["report_id"]
    client.patch(f"/reports/{report_id}", json={"status": "confirmed"})

    response = client.patch(f"/reports/{report_id}", json={"status": "new"})

    assert response.status_code == 409


def test_patch_unknown_report_id_returns_404():
    response = client.patch(f"/reports/{uuid.uuid4()}", json={"status": "confirmed"})
    assert response.status_code == 404

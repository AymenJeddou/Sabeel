"""Dashboard endpoints against the real database (same setup as test_reports.py)."""
import io
import uuid


def _submit(client, device_id: str) -> dict:
    files = {"photo": ("p.jpg", io.BytesIO(b"fake-bytes"), "image/jpeg")}
    form = {
        "device_report_id": f"test-{uuid.uuid4()}",
        "lat": "36.8", "lon": "10.18", "gps_accuracy_m": "4", "speed_kmh": "0",
        "direction_deg": "0", "captured_at": "2026-09-15T10:32:00Z", "source": "manual",
        "device_id": device_id,
    }
    return client.post("/reports", data=form, files=files).json()


def test_list_reports_filters_by_device_and_adds_dashboard_fields(client):
    device = f"test-device-{uuid.uuid4()}"
    created = _submit(client, device)

    rows = client.get("/reports", params={"device_id": device}).json()

    assert [r["report_id"] for r in rows] == [created["report_id"]]
    assert rows[0]["ref"].startswith("TN-") and rows[0]["cluster_size"] >= 1


def test_stats_shape(client):
    body = client.get("/stats").json()
    assert {"open", "fixed", "overdue", "weekly", "top_zones"} <= body.keys()
    assert len(body["weekly"]) == 10


def test_messages_round_trip_and_conversation_list(client):
    device = f"test-device-{uuid.uuid4()}"
    for sender, text in [("citizen", "Bonjour"), ("authority", "Bonjour, on s'en occupe.")]:
        assert client.post("/messages", json={"device_id": device, "sender": sender, "body": text}).status_code == 201

    thread = client.get("/messages", params={"device_id": device}).json()
    assert [m["sender"] for m in thread] == ["citizen", "authority"]
    convo = next(c for c in client.get("/conversations").json() if c["device_id"] == device)
    assert convo["count"] == 2 and convo["last_sender"] == "authority"


def test_reject_is_allowed_from_new(client):
    created = _submit(client, "test-device")
    response = client.patch(f"/reports/{created['report_id']}", json={"status": "rejected"})
    assert response.status_code == 200


def test_assistant_always_answers(client):
    # No LLM in CI: the data-only fallback must still answer.
    body = client.post("/assistant", json={"question": "Combien de nids-de-poule ouverts ?"}).json()
    assert body["source"] in ("llm", "fallback") and body["answer"]

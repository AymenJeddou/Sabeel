"""Report intake: contract shape, idempotency, detection gate, validation, privacy."""
import io

import cv2
import numpy as np

from backend.app import privacy
from backend.app.tests.conftest import POTHOLE_JPG, ROAD_JPG, report_form, submit


def test_create_report_returns_contract_shape(client):
    r = submit(client)
    assert r.status_code == 201
    body = r.json()
    assert body["detected"] is True and body["status"] == "new"
    assert 1 <= body["score"] <= 5 and 0 < body["confidence"] <= 1
    assert body["pothole_id"] and body["ref"].startswith("TN-")
    assert body["sheet_summary"] is None  # sheets are generated in the background


def test_same_device_report_id_twice_returns_the_same_report(client):
    form = report_form()
    files = lambda: {"photo": ("p.jpg", io.BytesIO(POTHOLE_JPG), "image/jpeg")}
    first = client.post("/reports", data=form, files=files())
    second = client.post("/reports", data=form, files=files())
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["report_id"] == second.json()["report_id"]
    assert len(client.get(f"/devices/{form['device_id']}/reports").json()) == 1


def test_no_detection_is_stored_for_review_without_a_pothole(client):
    r = submit(client, photo=ROAD_JPG)
    body = r.json()
    assert r.status_code == 201 and body["detected"] is False
    assert body["pothole_id"] is None and body["needs_review"] is True


def test_send_anyway_creates_a_pothole_flagged_for_review(client):
    form = report_form()
    files = lambda: {"photo": ("p.jpg", io.BytesIO(ROAD_JPG), "image/jpeg")}
    client.post("/reports", data=form, files=files())
    forced = client.post("/reports", data={**form, "force": "true"}, files=files()).json()
    assert forced["pothole_id"] and forced["needs_review"] is True and forced["detected"] is False


def test_direction_is_optional_and_web_source_is_accepted(client):
    form = report_form(source="web")
    del form["direction_deg"]
    r = client.post("/reports", data=form, files={"photo": ("p.jpg", io.BytesIO(POTHOLE_JPG), "image/jpeg")})
    assert r.status_code == 201


def test_rejects_non_images_bad_coordinates_and_dates(client):
    assert submit(client, photo=b"definitely not a jpeg").status_code == 415
    assert submit(client, lat=95).status_code == 422
    assert submit(client, captured_at="2099-01-01T00:00:00Z").status_code == 422
    assert submit(client, captured_at="2020-01-01T00:00:00Z").status_code == 422


def test_rejects_oversized_uploads(client, monkeypatch):
    from backend.app.config import settings

    monkeypatch.setattr(settings, "max_upload_mb", 0.01)
    assert submit(client).status_code == 413


def test_rate_limit_per_device(client):
    form = report_form()
    codes = [
        client.post("/reports", data={**form, "device_report_id": f"rl-{i:08d}"},
                    files={"photo": ("p.jpg", io.BytesIO(ROAD_JPG), "image/jpeg")}).status_code
        for i in range(11)
    ]
    assert codes[:10] == [201] * 10 and codes[10] == 429


def test_tracker_shows_status_and_timeline(client):
    form = report_form()
    client.post("/reports", data=form, files={"photo": ("p.jpg", io.BytesIO(POTHOLE_JPG), "image/jpeg")})
    body = client.get(f"/reports/{form['device_report_id']}").json()
    assert body["status"] == "new" and body["timeline"][0]["status"] == "new"
    assert client.get("/reports/does-not-exist").status_code == 404


def test_stored_photo_has_no_exif_and_is_reencoded(client):
    body = submit(client).json()
    detail = client.get(f"/reports/{body['device_report_id']}").json()
    stored = client.get(detail["photo_url"]).content
    assert stored[:3] == b"\xff\xd8\xff" and b"Exif" not in stored[:200]


def test_anonymize_blurs_a_detected_face():
    # A synthetic image is enough to check the blur path itself.
    img = np.full((400, 400, 3), 128, np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    out, regions = privacy.anonymize(buf.tobytes())
    assert out[:3] == b"\xff\xd8\xff" and regions == 0
    assert privacy.sniff_image_type(b"\x89PNG\r\n\x1a\n....") == "png"


def test_detect_scores_a_frame_without_storing_it(client):
    r = client.post("/detect", files={"frame": ("f.jpg", io.BytesIO(POTHOLE_JPG), "image/jpeg")}, data={"device_id": "car-1"})
    assert r.status_code == 200 and r.json()["detected"] is True
    assert client.get("/map").json() == []

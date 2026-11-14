"""Potholes: distinct-device confirmation, officer auth and scoping, status
changes, mark-fixed with AI check, "I see it too" confirmations, reopening."""
import io

from backend.app.tests.conftest import POTHOLE_JPG, ROAD_JPG, auth, report_form, run_jobs, submit

HERE = {"lat": 36.80650, "lon": 10.18150}


def confirmed_pothole(client) -> str:
    submit(client, device_id="phone-aaaaaaaa", **HERE)
    pid = submit(client, device_id="phone-bbbbbbbb", lat=36.80651, lon=10.18151).json()["pothole_id"]
    run_jobs(client)  # enrich -> routed to an office, then the sheet
    return pid


def tap(client, pid, kind, device="phone-cccccccc", lat=HERE["lat"], lon=HERE["lon"], acc=5):
    return client.post(f"/potholes/{pid}/confirmations",
                       json={"device_id": device, "kind": kind, "lat": lat, "lon": lon, "gps_accuracy_m": acc})


def test_same_phone_never_confirms_its_own_pothole(client):
    for _ in range(3):
        body = submit(client, device_id="phone-aaaaaaaa", **HERE).json()
    assert body["status"] == "new"
    assert len(client.get("/map").json()) == 1  # three reports, one pothole


def test_two_phones_within_5m_confirm_and_30m_stays_separate(client):
    submit(client, device_id="phone-aaaaaaaa", **HERE)
    near = submit(client, device_id="phone-bbbbbbbb", lat=36.80652, lon=10.18151).json()
    assert near["status"] == "confirmed"
    far = submit(client, device_id="phone-cccccccc", lat=36.80677, lon=10.18150).json()  # ~30 m north
    assert far["pothole_id"] != near["pothole_id"] and far["status"] == "new"


def test_officer_routes_need_a_valid_token(client):
    pid = confirmed_pothole(client)
    assert client.patch(f"/potholes/{pid}", json={"status": "rejected"}).status_code == 401
    assert client.patch(f"/potholes/{pid}", json={"status": "rejected"}, headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/authorities/me/queue").status_code == 401
    assert client.get("/conversations").status_code == 401


def test_offices_only_see_their_own_potholes(client):
    pid = confirmed_pothole(client)  # Tunis centre -> Municipalité de Tunis (offline routing)
    assert client.patch(f"/potholes/{pid}", json={"status": "rejected"}, headers=auth("mun-sfax")).status_code == 403
    tunis = client.get("/authorities/me/queue", headers=auth("mun-tunis")).json()
    sfax = client.get("/authorities/me/queue", headers=auth("mun-sfax")).json()
    ministry = client.get("/authorities/me/queue", headers=auth("ministry")).json()
    assert [r["pothole_id"] for r in tunis["items"]] == [pid]
    assert sfax["items"] == [] and ministry["total"] == 1


def test_public_detail_hides_private_fields_officer_detail_has_them(client):
    pid = confirmed_pothole(client)
    public = client.get(f"/potholes/{pid}").json()
    assert "reports" not in public and "sheet_text" not in public and "priority_score" not in public
    officer = client.get(f"/potholes/{pid}", headers=auth()).json()
    assert len(officer["reports"]) == 2 and officer["events"] and "priority_components" in officer


def test_patch_rules(client):
    pid = confirmed_pothole(client)
    h = auth()
    assert client.patch(f"/potholes/{pid}", json={"status": "fixed"}, headers=h).status_code == 409
    assert client.patch(f"/potholes/{pid}", json={"status": "sheet_sent"}, headers=h).status_code == 409
    r = client.patch(f"/potholes/{pid}", json={"status": "rejected", "note": "plaque d'égout"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    events = client.get(f"/potholes/{pid}", headers=h).json()["events"]
    assert any(e["kind"] == "status" and e["to_status"] == "rejected" and e["actor"] == "office:mun-tunis" for e in events)


def test_manual_confirmation_of_a_needs_review_pothole(client):
    form = report_form(device_id="phone-aaaaaaaa", **HERE, force="true")
    pid = client.post("/reports", data=form, files={"photo": ("p.jpg", io.BytesIO(ROAD_JPG), "image/jpeg")}).json()["pothole_id"]
    run_jobs(client)
    r = client.patch(f"/potholes/{pid}", json={"status": "confirmed"}, headers=auth())
    assert r.status_code == 200
    assert client.get(f"/potholes/{pid}", headers=auth()).json()["needs_review"] is False


def approve(client, pid):
    assert client.post(f"/potholes/{pid}/sheet/approve", headers=auth()).status_code == 200


def test_mark_fixed_needs_proof_and_runs_the_ai_check(client):
    pid = confirmed_pothole(client)
    approve(client, pid)
    url = f"/potholes/{pid}/fix"
    assert client.post(url, data={"note": "réparé"}, headers=auth()).status_code == 422  # no photo
    # Proof photo that still shows a pothole: fixed, but flagged.
    r = client.post(url, data={"note": "enrobé à chaud"}, files={"proof": ("f.jpg", io.BytesIO(POTHOLE_JPG), "image/jpeg")}, headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "fixed" and body["fix_check"]["detected"] is True and body["fix_verified"] is False


def test_clean_proof_photo_verifies_the_fix(client):
    pid = confirmed_pothole(client)
    approve(client, pid)
    r = client.post(f"/potholes/{pid}/fix", data={"note": "réparé"}, files={"proof": ("f.jpg", io.BytesIO(ROAD_JPG), "image/jpeg")}, headers=auth())
    assert r.json()["fix_verified"] is True


def test_confirmations_geofence_idempotency_and_promotion(client):
    pid = submit(client, device_id="phone-aaaaaaaa", **HERE).json()["pothole_id"]
    far = tap(client, pid, "seen", lat=36.8083)  # ~200 m away
    assert far.status_code == 403 and "Rapprochez" in far.json()["detail"]
    assert tap(client, pid, "seen", acc=80).status_code == 403
    first = tap(client, pid, "seen")
    assert first.status_code == 201 and first.json()["status"] == "confirmed"
    again = tap(client, pid, "seen")
    assert again.status_code == 200 and again.json()["created"] is False and again.json()["confirm_count"] == 1
    assert tap(client, pid, "fixed_ok").status_code == 409  # not fixed yet


def test_two_still_there_taps_reopen_a_fixed_pothole(client):
    pid = confirmed_pothole(client)
    approve(client, pid)
    client.post(f"/potholes/{pid}/fix", data={"note": "réparé"}, files={"proof": ("f.jpg", io.BytesIO(ROAD_JPG), "image/jpeg")}, headers=auth())
    before = client.get(f"/potholes/{pid}", headers=auth()).json()["priority_score"]
    tap(client, pid, "not_fixed", device="phone-dddddddd")
    r = tap(client, pid, "not_fixed", device="phone-eeeeeeee")
    assert r.json()["status"] == "reopened"
    after = client.get(f"/potholes/{pid}", headers=auth()).json()
    assert after["priority_score"] > before and after["priority_components"]["reopened"] == 10
    assert pid in [i["pothole_id"] for i in client.get("/authorities/me/queue", headers=auth()).json()["items"]]


def test_two_not_a_pothole_taps_flag_review_and_create_labels(client):
    pid = confirmed_pothole(client)
    tap(client, pid, "not_pothole", device="phone-dddddddd")
    tap(client, pid, "not_pothole", device="phone-eeeeeeee")
    assert client.get(f"/potholes/{pid}", headers=auth()).json()["needs_review"] is True


def test_new_report_on_a_recently_fixed_pothole_counts_as_still_there(client):
    pid = confirmed_pothole(client)
    approve(client, pid)
    client.post(f"/potholes/{pid}/fix", data={"note": "réparé"}, files={"proof": ("f.jpg", io.BytesIO(ROAD_JPG), "image/jpeg")}, headers=auth())
    again = submit(client, device_id="phone-ffffffff", **HERE).json()
    assert again["pothole_id"] == pid
    assert client.get(f"/potholes/{pid}", headers=auth()).json()["not_fixed_count"] == 1


def test_device_history_lists_every_report_with_pothole_status(client):
    form = report_form(device_id="phone-aaaaaaaa", **HERE)
    client.post("/reports", data=form, files={"photo": ("p.jpg", io.BytesIO(POTHOLE_JPG), "image/jpeg")})
    rows = client.get("/devices/phone-aaaaaaaa/reports").json()
    assert rows[0]["device_report_id"] == form["device_report_id"] and rows[0]["ref"].startswith("TN-")


def test_messages_authority_reply_needs_a_token(client):
    msg = {"device_id": "phone-aaaaaaaa", "sender": "authority", "body": "Bonjour"}
    assert client.post("/messages", json=msg).status_code == 401
    assert client.post("/messages", json=msg, headers=auth()).status_code == 201
    assert client.post("/messages", json={**msg, "sender": "citizen"}).status_code == 201
    assert [m["sender"] for m in client.get("/messages", params={"device_id": "phone-aaaaaaaa"}).json()] == ["authority", "citizen"]
    convo = client.get("/conversations", headers=auth()).json()
    assert convo[0]["count"] == 2


def test_assistant_answers_from_data_when_the_llm_is_down(client):
    confirmed_pothole(client)
    body = client.post("/assistant", json={"question": "Combien de nids-de-poule ouverts ?"}, headers=auth()).json()
    assert body["source"] == "fallback" and "ouverts" in body["answer"] and body["refs"]

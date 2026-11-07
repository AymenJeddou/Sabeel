"""Sheet job queue: generation, retries with backoff, failure, review,
approval, PDF and fingerprint verification (issue #25)."""
from datetime import timedelta

from sqlalchemy import select, update

from backend.app import rag_client
from backend.app.db_models import Job, Pothole
from backend.app.potholes import now_utc
from backend.app.tests.conftest import auth, db_call, run_jobs, submit

HERE = {"lat": 36.80650, "lon": 10.18150}


def confirmed(client) -> str:
    submit(client, device_id="phone-aaaaaaaa", **HERE)
    return submit(client, device_id="phone-bbbbbbbb", **HERE).json()["pothole_id"]


def jobs_of(client, pid):
    return db_call(client, lambda db: _jobs(db, pid))


async def _jobs(db, pid):
    return [(j.type, j.status, j.attempts) for j in (await db.execute(select(Job).where(Job.pothole_id == pid).order_by(Job.id))).scalars()]


def make_due(client):
    return db_call(client, lambda db: db.execute(update(Job).where(Job.status == "queued").values(next_attempt_at=now_utc() - timedelta(seconds=1))))


def test_confirmation_queues_enrichment_then_sheet(client):
    pid = confirmed(client)
    assert {t for t, *_ in jobs_of(client, pid)} == {"enrich", "sheet"}
    run_jobs(client)
    sheet = client.get(f"/potholes/{pid}/sheet", headers=auth()).json()
    assert sheet["sheet_status"] == "generated" and sheet["sheet_citations"][0]["rule_id"] == "TN-CCL2018-ART69"
    assert client.get(f"/potholes/{pid}").json()["status"] == "confirmed"  # not sent until approved


def test_rag_down_retries_with_backoff_then_recovers(client, monkeypatch):
    async def down(**_):
        return None

    good = rag_client.generate
    monkeypatch.setattr(rag_client, "generate", down)
    pid = confirmed(client)
    run_jobs(client)
    sheet_job = [j for j in jobs_of(client, pid) if j[0] == "sheet"][0]
    assert sheet_job[1] == "queued" and sheet_job[2] == 1  # retried later, intake unaffected
    assert run_jobs(client) == 0  # backoff: not due yet

    monkeypatch.setattr(rag_client, "generate", good)
    make_due(client)
    run_jobs(client)
    assert client.get(f"/potholes/{pid}/sheet", headers=auth()).json()["sheet_status"] == "generated"


def test_failed_job_is_visible_and_retryable(client, monkeypatch):
    from backend.app.config import settings

    async def down(**_):
        return None

    good = rag_client.generate
    monkeypatch.setattr(rag_client, "generate", down)
    monkeypatch.setattr(settings, "job_max_attempts", 2)
    pid = confirmed(client)
    run_jobs(client)
    make_due(client)
    run_jobs(client)
    sheet = client.get(f"/potholes/{pid}/sheet", headers=auth()).json()
    assert sheet["sheet_status"] == "failed" and sheet["sheet_job"]["last_error"]

    monkeypatch.setattr(rag_client, "generate", good)
    assert client.post(f"/potholes/{pid}/sheet/retry", headers=auth()).json()["sheet_status"] == "queued"
    run_jobs(client)
    assert client.get(f"/potholes/{pid}/sheet", headers=auth()).json()["sheet_status"] == "generated"


def test_edit_keeps_the_original_and_approval_sends_the_sheet(client):
    pid = confirmed(client)
    run_jobs(client)
    h = auth()
    edited = "Fiche corrigée : balisage immédiat puis enrobé à chaud."
    assert client.patch(f"/potholes/{pid}/sheet", json={"sheet_text": edited}, headers=h).status_code == 200
    detail = client.get(f"/potholes/{pid}", headers=h).json()
    assert detail["sheet_edited"] is True
    assert any(e["kind"] == "sheet_edited" and "Fiche de travaux" in e["data"]["previous_text"] for e in detail["events"])

    r = client.post(f"/potholes/{pid}/sheet/approve", headers=h).json()
    assert r["status"] == "sheet_sent" and r["sheet_status"] == "approved" and len(r["fingerprint"]) == 16
    assert client.post(f"/potholes/{pid}/sheet/approve", headers=h).status_code == 409
    # The citizen tracker now shows "Transmis" and the first lines of the sheet.
    report = client.get("/devices/phone-aaaaaaaa/reports").json()[0]
    assert report["status"] == "sheet_sent"


def test_approval_keeps_only_the_best_photo(client):
    pid = confirmed(client)
    run_jobs(client)
    client.post(f"/potholes/{pid}/sheet/approve", headers=auth())
    photos = [r["photo_url"] for r in client.get(f"/potholes/{pid}", headers=auth()).json()["reports"]]
    assert sum(p is not None for p in photos) == 1


def test_pdf_and_qr_verification(client):
    pid = confirmed(client)
    run_jobs(client)
    assert client.get(f"/potholes/{pid}/sheet.pdf", headers=auth()).status_code == 200
    fp = client.post(f"/potholes/{pid}/sheet/approve", headers=auth()).json()["fingerprint"]
    pdf = client.get(f"/potholes/{pid}/sheet.pdf", headers=auth())
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content[:5] == b"%PDF-"
    assert client.get(f"/public/potholes/{pid}/verify", params={"h": fp}).json()["valid"] is True
    assert client.get(f"/public/potholes/{pid}/verify", params={"h": "0123456789abcdef"}).json()["valid"] is False


def test_low_severity_potholes_get_no_sheet_and_can_be_fixed_directly(client):
    import io

    from backend.app import potholes as svc
    from backend.app.tests.conftest import ROAD_JPG

    submit(client, device_id="phone-aaaaaaaa", **HERE)
    db_call(client, lambda db: db.execute(update(Pothole).values(severity=2)))

    async def confirm(db):
        p = (await db.execute(select(Pothole))).scalars().first()
        await svc.set_status(db, p, svc.S.CONFIRMED, "test")
        return p.pothole_id

    pid = db_call(client, confirm)
    assert [t for t, *_ in jobs_of(client, pid)] == ["enrich"]
    run_jobs(client)
    r = client.post(f"/potholes/{pid}/fix", data={"note": "colmaté à froid"},
                    files={"proof": ("f.jpg", io.BytesIO(ROAD_JPG), "image/jpeg")}, headers=auth())
    assert r.status_code == 200 and r.json()["status"] == "fixed"

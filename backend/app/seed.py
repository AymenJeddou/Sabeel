"""Demo data for the dashboard and the mobile app: real Tunis streets, real
pothole photos, the vision model's real scores, ~10 weeks of history and a few
citizen <-> authority conversations.

    python -m backend.app.seed            (run from the repo root)

Idempotent: removes previous seed rows (device_id "seed-...") and the pytest /
curl leftovers ("test-..." / "e2e-...") first, then inserts fresh ones.

Sources:
- Street coordinates and districts: OpenStreetMap Nominatim, fetched once on
  2026-09-30 and frozen below.
- Photos: Wikimedia Commons "Category:Potholes" (static/photos/_seed/sources.json
  lists each file's title and URL), downloaded into static/photos/_seed/.
"""
import asyncio
import json
import random
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, or_

from backend.app.db import async_session
from backend.app.db_models import Message, Report
from backend.app.rag_client import generate as rag_generate
from backend.app.routers.reports import STATIC_PHOTOS_DIR
from backend.app.schemas import ReportSource
from backend.app.status import ReportStatus

SEED_DIR = STATIC_PHOTOS_DIR / "_seed"

# (street, district, lat, lon, office) -- national roads go to the DGPC.
STREETS = [
    ("Avenue Habib Bourguiba", "Tunis Centre", 36.800537, 10.187926, "Municipality"),
    ("Avenue Mohamed V", "Tunis Centre", 36.801232, 10.186305, "Municipality"),
    ("Avenue de la Liberté", "Borj Flifel", 36.805311, 10.150100, "Municipality"),
    ("Avenue de Paris", "Tunis Centre", 36.802869, 10.180916, "Municipality"),
    ("Rue de Marseille", "Tunis Centre", 36.803750, 10.181782, "Municipality"),
    ("Avenue Hédi Chaker", "Taieb El M'Hiri", 36.816856, 10.180951, "Municipality"),
    ("Avenue de Carthage", "Lac de Tunis", 36.789159, 10.183056, "Municipality"),
    ("Avenue Habib Thameur", "Le Bardo", 36.810041, 10.136848, "Municipality"),
    ("Avenue Taïeb Mhiri", "Bab El Khadra", 36.810827, 10.174330, "Municipality"),
    ("Avenue Alain Savary", "Les Jardins", 36.830222, 10.186842, "Municipality"),
    ("Avenue Ali Belhouane", "El Hafsia", 36.805326, 10.168758, "Municipality"),
    ("Avenue Farhat Hached", "Lac de Tunis", 36.797889, 10.185494, "Municipality"),
    ("Rue du Lac Léman", "Les Berges du Lac", 36.840480, 10.244134, "Municipality"),
    ("Avenue Jugurtha", "Mutuelleville", 36.830797, 10.169456, "Municipality"),
    ("Avenue Mongi Slim", "Ksar Saïd", 36.813562, 10.130166, "Municipality"),
    ("Rue d'Espagne", "Bab El Bhar", 36.796889, 10.177569, "Municipality"),
    ("Avenue Louis Braille", "Les Jardins", 36.826133, 10.188325, "Municipality"),
    ("Avenue de Londres", "Tunis Centre", 36.805901, 10.178469, "Municipality"),
    ("Avenue Habib Bourguiba", "La Marsa", 36.864390, 10.310499, "Municipality"),
    ("Avenue de l'Environnement", "Ariana", 36.861913, 10.201903, "Municipality"),
    ("Avenue Habib Bourguiba", "Nouvelle Ariana", 36.852688, 10.185005, "Municipality"),
    ("Avenue Hédi Nouira", "El Menzah 7", 36.855860, 10.159110, "Municipality"),
    ("Avenue de l'Indépendance", "Khaznadar", 36.805897, 10.132883, "Municipality"),
    ("Route Nationale 1", "Radès", 36.753441, 10.249427, "DGPC"),
    ("Route Nationale 9", "La Marsa", 36.875413, 10.323792, "DGPC"),
]

CONVERSATIONS = {
    "seed-citizen-01": [
        ("citizen", "Bonjour, j'ai signalé un nid-de-poule avenue Habib Bourguiba il y a une semaine. Est-ce qu'il est pris en charge ?"),
        ("authority", "Bonjour, oui : la fiche a été transmise au service technique de la municipalité. Intervention prévue cette semaine."),
        ("citizen", "Merci ! Il est vraiment dangereux pour les motos le soir."),
    ],
    "seed-citizen-02": [
        ("citizen", "السلام عليكم، في حفرة كبيرة في شارع الحرية قدام المدرسة، الكرهبة طاحت فيها."),
        ("authority", "وعليكم السلام، شكرا على الإبلاغ. الإشارة وصلتنا وتم تأكيدها، الفريق التقني باش يتنقل في أقرب وقت."),
    ],
    "seed-citizen-03": [
        ("citizen", "La route nationale 1 vers Radès est pleine de trous après la pluie, vous êtes au courant ?"),
        ("authority", "Oui, plusieurs signalements ont été regroupés. Le dossier est transmis à la DGPC, compétente pour les routes nationales."),
        ("citizen", "D'accord, merci pour la réponse rapide."),
        ("authority", "Avec plaisir. Vous pouvez suivre l'état dans « Mes Rapports »."),
    ],
    "seed-citizen-04": [
        ("citizen", "Le nid-de-poule rue de Marseille a été réparé, merci !"),
    ],
    "seed-citizen-05": [
        ("citizen", "Bonsoir, j'ai pris en photo une plaque d'égout et l'appli l'a comptée comme nid-de-poule, désolé."),
        ("authority", "Aucun souci, le signalement a été vérifié et classé comme faux positif. Merci de votre vigilance !"),
    ],
}


def _photo(report_id: uuid.UUID, source: Path) -> str:
    shutil.copy(source, STATIC_PHOTOS_DIR / f"{report_id}.jpg")
    return f"/static/photos/{report_id}.jpg"


async def main() -> None:
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    photos = json.loads((SEED_DIR / "sources.json").read_text(encoding="utf-8"))
    detected = [p for p in photos if p["score"]]
    undetected = [p for p in photos if not p["score"]]
    false_pos = [(SEED_DIR / "fp_manhole.jpg", 3, 0.78), (SEED_DIR / "fp_crack.jpg", 4, 0.58)]

    # One pothole per street, plus a second one further along 8 of them.
    spots = [(s, 0.0, 0.0) for s in STREETS] + [
        (s, rng.uniform(-0.0015, 0.0015), rng.uniform(-0.0015, 0.0015)) for s in rng.sample(STREETS, 8)
    ]
    reports: list[Report] = []
    need_sheet: list[Report] = []

    for i, ((street, district, lat, lon, office), dlat, dlon) in enumerate(spots):
        age = rng.uniform(1, 70)  # days since the first report
        if i < 2:  # the two false positives, rejected after triage
            path, score, conf = false_pos[i]
            status = ReportStatus.REJECTED
        elif i % 7 == 3:  # model found nothing: waiting for a human look
            p = rng.choice(undetected)
            path, score, conf, status = Path(p["file"]).name, None, None, ReportStatus.NEW
        else:
            p = rng.choice(detected)
            path, score, conf = Path(p["file"]).name, p["score"], p["confidence"]
            # Older potholes are more likely to be repaired already.
            status = rng.choices(
                [ReportStatus.FIXED, ReportStatus.SHEET_SENT, ReportStatus.CONFIRMED, ReportStatus.NEW],
                weights=[max(age - 10, 0), 30, 25, 15 if age < 12 else 3],
            )[0]
        source_photo = SEED_DIR / Path(path).name
        cluster_id = uuid.uuid4() if status != ReportStatus.NEW else None
        size = 1 if status in (ReportStatus.NEW, ReportStatus.REJECTED) else rng.choice([2, 2, 3, 3, 4])
        first_at = now - timedelta(days=age)
        repaired_after = timedelta(days=rng.uniform(1, {5: 3, 4: 8, 3: 16}.get(score or 3, 20)))

        for k in range(size):
            created = first_at + timedelta(hours=rng.uniform(2, 60)) * k
            report_id = uuid.uuid4()
            member_status = status if k == size - 1 else (
                ReportStatus.FIXED if status == ReportStatus.FIXED else ReportStatus.CONFIRMED
            )
            r = Report(
                report_id=report_id,
                device_report_id=str(uuid.uuid4()),
                photo_url=_photo(report_id, source_photo),
                lat=lat + dlat + rng.uniform(-0.00002, 0.00002),
                lon=lon + dlon + rng.uniform(-0.00002, 0.00002),
                gps_accuracy_m=round(rng.uniform(3, 12), 1),
                speed_kmh=round(rng.choice([0, 0, 0, rng.uniform(15, 50)]), 1),
                direction_deg=round(rng.uniform(0, 359), 1),
                captured_at=created,
                source=rng.choice([ReportSource.MANUAL] * 4 + [ReportSource.DRIVING_MODE]),
                score=score,
                confidence=conf,
                status=member_status,
                cluster_id=cluster_id,
                target_office=office if member_status != ReportStatus.NEW else None,
                device_id=f"seed-citizen-{rng.randint(1, 12):02d}",
                address=f"{street}, {district}",
                created_at=created,
                updated_at=min(first_at + repaired_after, now) if member_status == ReportStatus.FIXED else created,
            )
            reports.append(r)
            if member_status in (ReportStatus.SHEET_SENT, ReportStatus.FIXED) and k == size - 1:
                need_sheet.append(r)

    # Real work sheets from the RAG service (4 at a time; ~10 s each).
    gate = asyncio.Semaphore(4)

    async def sheet(r: Report) -> None:
        async with gate:
            result = await rag_generate(lat=r.lat, lon=r.lon, score=r.score or 3)
        if result:
            r.sheet_text = result["sheet_text"]

    print(f"Generating {len(need_sheet)} work sheets via the RAG service...")
    await asyncio.gather(*(sheet(r) for r in need_sheet))

    async with async_session() as db:
        await db.execute(
            delete(Report).where(
                or_(
                    Report.device_id.like("seed-%"),
                    Report.device_report_id.like("test-%"),
                    Report.device_report_id.like("e2e-%"),
                )
            )
        )
        await db.execute(delete(Message).where(or_(Message.device_id.like("seed-%"), Message.device_id.like("test-%"))))
        db.add_all(reports)
        for device_id, thread in CONVERSATIONS.items():
            start = now - timedelta(days=rng.uniform(1, 12))
            for n, (sender, body) in enumerate(thread):
                db.add(Message(device_id=device_id, sender=sender, body=body, created_at=start + timedelta(minutes=37 * n)))
        await db.commit()

    print(f"Seeded {len(reports)} reports ({len(spots)} potholes) and {len(CONVERSATIONS)} conversations.")


if __name__ == "__main__":
    asyncio.run(main())

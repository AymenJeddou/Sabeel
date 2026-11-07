"""Demo data for the dashboard, the public page and the mobile app.

    python -m backend.app.seed              (from the repo root)
    python -m backend.app.seed --extra 5000 (also 5,000 synthetic potholes for load tests)

Wipes potholes, reports, events, jobs, labels and messages, then creates:
- the pilot offices with demo tokens `demo-<code>` (printed at the end);
- ~45 potholes on real Tunis, Sousse and Sfax streets, each with 1-4 citizen
  reports, real pothole photos and the vision model's real scores and boxes;
- ~10 weeks of history replayed through the audit log: confirmations, work
  sheets (from the RAG service when it runs, else a template that quotes the
  real Law 2018-29 / 86-17 rules), approvals, repairs, one escalation, one
  reopening, two rejected false positives;
- a few citizen <-> authority conversations (French and Tunisian Arabic).

Sources: street coordinates from OpenStreetMap Nominatim (frozen 2026-09-30);
photos from Wikimedia Commons "Category:Potholes" (static/photos/_seed/sources.json).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, text

from backend.app import priority, sla
from backend.app.db import async_session, engine
from backend.app.db_models import Message, Office, Pothole, Report, ReportEvent
from backend.app.migrate import migrate
from backend.app.pdf import sheet_fingerprint
from backend.app.rag_client import generate as rag_generate
from backend.app.scripts.seed_offices import upsert_offices
from backend.app.storage import PHOTOS_DIR

SEED_DIR = PHOTOS_DIR / "_seed"

# (street, district, municipality, region, lat, lon, road_class, road_ref, office code)
STREETS = [
    ("Avenue Habib Bourguiba", "Tunis Centre", "Tunis", "Tunis", 36.800537, 10.187926, "national", "RN9", "dre-tunis"),
    ("Avenue Mohamed V", "Tunis Centre", "Tunis", "Tunis", 36.801232, 10.186305, "urbain_principal", None, "mun-tunis"),
    ("Avenue de la Liberté", "Borj Flifel", "Tunis", "Tunis", 36.805311, 10.150100, "urbain_secondaire", None, "mun-tunis"),
    ("Avenue de Paris", "Tunis Centre", "Tunis", "Tunis", 36.802869, 10.180916, "urbain_principal", None, "mun-tunis"),
    ("Rue de Marseille", "Tunis Centre", "Tunis", "Tunis", 36.803750, 10.181782, "urbain_secondaire", None, "mun-tunis"),
    ("Avenue Hédi Chaker", "Taieb El M'Hiri", "Tunis", "Tunis", 36.816856, 10.180951, "urbain_principal", None, "mun-tunis"),
    ("Avenue de Carthage", "Lac de Tunis", "Tunis", "Tunis", 36.789159, 10.183056, "urbain_principal", None, "mun-tunis"),
    ("Avenue Habib Thameur", "Le Bardo", "Le Bardo", "Tunis", 36.810041, 10.136848, "urbain_principal", None, "mun-le-bardo"),
    ("Avenue Taïeb Mhiri", "Bab El Khadra", "Tunis", "Tunis", 36.810827, 10.174330, "urbain_principal", None, "mun-tunis"),
    ("Avenue Alain Savary", "Les Jardins", "Tunis", "Tunis", 36.830222, 10.186842, "urbain_principal", None, "mun-tunis"),
    ("Avenue Ali Belhouane", "El Hafsia", "Tunis", "Tunis", 36.805326, 10.168758, "urbain_secondaire", None, "mun-tunis"),
    ("Avenue Farhat Hached", "Lac de Tunis", "Tunis", "Tunis", 36.797889, 10.185494, "urbain_principal", None, "mun-tunis"),
    ("Rue du Lac Léman", "Les Berges du Lac", "Tunis", "Tunis", 36.840480, 10.244134, "urbain_secondaire", None, "mun-tunis"),
    ("Avenue Jugurtha", "Mutuelleville", "Tunis", "Tunis", 36.830797, 10.169456, "urbain_secondaire", None, "mun-tunis"),
    ("Rue d'Espagne", "Bab El Bhar", "Tunis", "Tunis", 36.796889, 10.177569, "urbain_secondaire", None, "mun-tunis"),
    ("Avenue de Londres", "Tunis Centre", "Tunis", "Tunis", 36.805901, 10.178469, "urbain_secondaire", None, "mun-tunis"),
    ("Avenue Habib Bourguiba", "La Marsa", "La Marsa", "Tunis", 36.864390, 10.310499, "urbain_principal", None, "mun-la-marsa"),
    ("Avenue de l'Environnement", "Ariana", "Ariana", "Ariana", 36.861913, 10.201903, "urbain_principal", None, "mun-ariana"),
    ("Avenue Habib Bourguiba", "Nouvelle Ariana", "Ariana", "Ariana", 36.852688, 10.185005, "urbain_principal", None, "mun-ariana"),
    ("Avenue Hédi Nouira", "El Menzah 7", "Ariana", "Ariana", 36.855860, 10.159110, "urbain_principal", None, "mun-ariana"),
    ("Rue de Kaboul", "Ennasr", "Ariana", "Ariana", 36.856500, 10.163000, "urbain_secondaire", None, "mun-ariana"),
    ("Route Nationale 1", "Radès", "Radès", "Ben Arous", 36.753441, 10.249427, "national", "RN1", "dre-ben-arous"),
    ("Route Nationale 9", "La Marsa", "La Marsa", "Tunis", 36.875413, 10.323792, "national", "RN9", "dre-tunis"),
    ("Boulevard Yahia Ibn Omar", "Sousse", "Sousse", "Sousse", 35.828300, 10.637200, "urbain_secondaire", None, "mun-sousse"),
    ("Avenue Hédi Chaker", "Sfax", "Sfax", "Sfax", 34.737900, 10.760000, "urbain_principal", None, "mun-sfax"),
]

ROAD_TYPE = {"national": "urbain_principal", "urbain_principal": "urbain_principal", "urbain_secondaire": "urbain_secondaire"}

CONVERSATIONS = {
    "seed-citizen-01": [
        ("citizen", "Bonjour, j'ai signalé un nid-de-poule avenue Mohamed V il y a une semaine. Est-ce qu'il est pris en charge ?"),
        ("authority", "Bonjour, oui : la fiche a été approuvée et transmise au service technique. Intervention prévue cette semaine."),
        ("citizen", "Merci ! Il est vraiment dangereux pour les motos le soir."),
    ],
    "seed-citizen-02": [
        ("citizen", "السلام عليكم، في حفرة كبيرة في شارع الحرية قدام المدرسة، الكرهبة طاحت فيها."),
        ("authority", "وعليكم السلام، شكرا على الإبلاغ. الإشارة وصلتنا وتم تأكيدها، الفريق التقني باش يتنقل في أقرب وقت."),
    ],
    "seed-citizen-03": [
        ("citizen", "La route nationale 1 vers Radès est pleine de trous après la pluie, vous êtes au courant ?"),
        ("authority", "Oui, plusieurs signalements ont été regroupés. Le dossier est transmis à la Direction régionale de l'Équipement, compétente pour les routes nationales."),
        ("citizen", "D'accord, merci pour la réponse rapide."),
    ],
    "seed-citizen-04": [("citizen", "Le nid-de-poule rue de Marseille a été réparé, merci !")],
    "seed-citizen-05": [
        ("citizen", "Bonsoir, j'ai pris en photo une plaque d'égout et l'appli l'a comptée comme nid-de-poule, désolé."),
        ("authority", "Aucun souci, le signalement a été vérifié et classé comme faux positif. Merci de votre vigilance !"),
    ],
}


def template_sheet(street: str, district: str, severity: int, office: Office, road_class: str) -> tuple[str, list[dict]]:
    """Used when the RAG service isn't running: quotes the real rules only."""
    if road_class == "national":
        cite = {"rule_id": "TN-LOI86-17-ART3", "source": "Loi n°86-17 du 7 mars 1986 portant refonte de la législation relative au domaine public routier de l'État",
                "excerpt": "Les routes classées nationales font partie du domaine public routier de l'État"}
    else:
        cite = {"rule_id": "TN-CCL2018-ART69", "source": "Loi organique n°2018-29 du 9 mai 2018, Code des Collectivités Locales, Article 69",
                "excerpt": "les avenues et les rues, les places publiques... les routes publiques ainsi que leurs dépendances"}
    text_ = (
        f"Fiche de travaux — nid-de-poule {street}, {district}.\n"
        f"Gravité : {severity}/5. Méthode : {sla.METHOD[severity]}.\n"
        f"Bureau responsable : {office.name} (voie {'classée nationale' if road_class == 'national' else 'communale'}).\n"
        f"Références: {cite['rule_id']}"
    )
    return text_, [cite]


async def build(rng: random.Random, offices: dict[str, Office]) -> tuple[list, list, list]:
    from backend.app.vision_client import run_inference

    now = datetime.now(timezone.utc)
    photos = json.loads((SEED_DIR / "sources.json").read_text(encoding="utf-8"))
    vision: dict[str, dict] = {}
    for name in [Path(p["file"]).name for p in photos] + ["fp_manhole.jpg", "fp_crack.jpg"]:
        vision[name] = run_inference((SEED_DIR / name).read_bytes(), "manual")
    detected = [n for n, v in vision.items() if v["score"]]
    undetected = [n for n, v in vision.items() if not v["score"] and not n.startswith("fp_")]

    spots = [(s, 0.0, 0.0) for s in STREETS] + [
        (s, rng.uniform(-0.0012, 0.0012), rng.uniform(-0.0012, 0.0012)) for s in rng.sample(STREETS, 20)
    ]
    potholes, reports, events = [], [], []
    sheets_needed = []

    def ev(p, at, actor, kind, frm=None, to=None, note=None, data=None):
        events.append(ReportEvent(pothole_id=p.pothole_id, actor=actor, kind=kind, from_status=frm, to_status=to,
                                  note=note, data=data, created_at=at))

    for i, ((street, district, municipality, region, lat, lon, road_class, ref, code), dlat, dlon) in enumerate(spots):
        age = rng.uniform(0.5, 70)
        created = now - timedelta(days=age)
        office = offices[code]
        if i < 2:
            kind, photo = "rejected", ["fp_manhole.jpg", "fp_crack.jpg"][i]
        elif i % 9 == 4:
            kind, photo = "review", rng.choice(undetected)
        else:
            photo = rng.choice(detected)
            kind = rng.choices(["fixed", "sheet_sent", "confirmed", "new"],
                               weights=[max(age - 8, 0), 30, 22, 14 if age < 10 else 2])[0]
        if kind in ("confirmed", "sheet_sent", "new", "review"):
            # Open potholes in a real city are mostly recent; old ones get fixed.
            age = rng.uniform(0.5, 16)
            created = now - timedelta(days=age)
        v = vision[photo]
        severity = v["score"] or rng.choice([2, 3])
        n_reports = 1 if kind in ("new", "review", "rejected") else rng.choice([2, 2, 3, 3, 4])
        p = Pothole(
            pothole_id=uuid.uuid4(), status="new", lat=lat + dlat, lon=lon + dlon, severity=severity,
            max_confidence=v["confidence"], road_type=ROAD_TYPE.get(road_class, "urbain_secondaire"), road_class=road_class,
            road_name=street if not ref else street, road_ref=ref, region=region, municipality=municipality,
            address_label=f"{street}, {district}", enrichment_source="osm", target_office_id=office.office_id,
            needs_review=kind == "review", report_count=n_reports, device_count=n_reports,
            created_at=created, updated_at=created, priority_components={},
        )
        ev(p, created, "device:seed", "created", to="new")
        for k in range(n_reports):
            at = created + timedelta(hours=rng.uniform(1, 30)) * k
            reports.append(Report(
                report_id=uuid.uuid4(), device_report_id=f"seed-{uuid.uuid4()}", pothole_id=p.pothole_id,
                photo_url=f"/static/photos/_seed/{photo}", lat=p.lat + rng.uniform(-0.00002, 0.00002),
                lon=p.lon + rng.uniform(-0.00002, 0.00002), gps_accuracy_m=round(rng.uniform(3, 12), 1),
                speed_kmh=round(rng.choice([0, 0, 0, rng.uniform(15, 45)]), 1), direction_deg=round(rng.uniform(0, 359), 1),
                captured_at=at, source=rng.choice(["manual"] * 5 + ["driving_mode", "web"]), score=v["score"],
                confidence=v["confidence"], detected=v["score"] is not None, needs_review=v["score"] is None,
                boxes=v["boxes"], inference_ms=v["inference_ms"], status="new",
                device_id=f"seed-citizen-{rng.randint(1, 14):02d}", created_at=at, updated_at=at,
            ))
        t = created + timedelta(hours=rng.uniform(2, 30))
        if kind == "rejected":
            p.status, p.updated_at = "rejected", t
            ev(p, t, "office:mun-tunis", "status", "new", "rejected", "plaque d'égout / fissure, pas un nid-de-poule")
        if kind in ("confirmed", "sheet_sent", "fixed"):
            p.status, p.confirmed_at = "confirmed", t
            p.sla_due_at = sla.due_at(t, severity)
            ev(p, t, "system", "status", "new", "confirmed", f"{n_reports} appareils distincts")
            if severity >= 3:
                p.sheet_status = "generated"
                p.sheet_generated_at = t + timedelta(minutes=rng.uniform(1, 5))
                sheets_needed.append((p, street, district, office))
                ev(p, p.sheet_generated_at, "system", "sheet_generated")
        if kind in ("sheet_sent", "fixed") and severity >= 3:
            at = p.sheet_generated_at + timedelta(hours=rng.uniform(1, 30))
            p.status, p.sheet_status, p.sheet_approved_at, p.sheet_approved_by = "sheet_sent", "approved", at, office.name
            ev(p, at, f"office:{office.code}", "status", "confirmed", "sheet_sent", "fiche approuvée")
        if kind == "fixed":
            deadline = sla.deadline_for(severity) or timedelta(days=20)
            at = min((p.confirmed_at or t) + deadline * rng.uniform(0.3, 1.3), now - timedelta(hours=2))
            p.fixed_at, p.updated_at = at, at
            frm = p.status
            p.status, p.sla_due_at = "fixed", None
            p.fixed_note, p.fixed_proof_url = "Réparation à l'enrobé à chaud, compactage.", None
            p.fix_check = {"detected": False, "confidence": None, "score": None, "boxes": [], "checked_at": at.isoformat()}
            p.fix_verified = True
            p.fixed_ok_count = rng.choice([0, 1, 2])
            ev(p, at, f"office:{office.code}", "status", frm, "fixed", p.fixed_note)
            ev(p, at, "system", "fix_check_passed")
        potholes.append(p)

    # One escalation and one reopening for the demo story.
    overdue = [p for p in potholes if p.status in ("confirmed", "sheet_sent") and p.sla_due_at and p.severity == 5]
    if overdue:
        p = overdue[0]
        p.confirmed_at, p.sla_due_at = now - timedelta(days=6), now - timedelta(days=4)
        parent = next(o for o in offices.values() if o.office_id == offices_by_id(offices)[p.target_office_id].parent_office_id)
        ev(p, now - timedelta(hours=20), "system", "escalated", note=f"{offices_by_id(offices)[p.target_office_id].name} → {parent.name}")
        p.target_office_id, p.escalated_at = parent.office_id, now - timedelta(hours=20)
    fixed = [p for p in potholes if p.status == "fixed"]
    if fixed:
        p = fixed[-1]
        p.status, p.reopened_at, p.not_fixed_count, p.fix_verified = "reopened", now - timedelta(days=1), 2, False
        p.confirmed_at, p.sla_due_at, p.fixed_at = now - timedelta(days=1), sla.due_at(now - timedelta(days=1), p.severity), None
        ev(p, now - timedelta(days=1), "system", "status", "fixed", "reopened", "2 citoyens : toujours là")

    # Work sheets: the real RAG service if it answers, else the rule-quoting template.
    gate = asyncio.Semaphore(4)

    async def sheet(item):
        p, street, district, office = item
        async with gate:
            result = await rag_generate(
                lat=p.lat, lon=p.lon, score=p.severity, road_type=p.road_type, office_name=office.name,
                address=p.address_label, jurisdiction="state" if p.road_class == "national" else "municipal")
        if result:
            p.sheet_text, p.sheet_citations = result["sheet_text"], result["rule_citations"]
        else:
            p.sheet_text, p.sheet_citations = template_sheet(street, district, p.severity, office, p.road_class)
        p.sheet_text_original = p.sheet_text
        if p.sheet_status == "approved":
            p.sheet_hash = sheet_fingerprint(p, office.code)

    print(f"Writing {len(sheets_needed)} work sheets (RAG service if running, template otherwise)...")
    await asyncio.gather(*(sheet(x) for x in sheets_needed))

    for p in potholes:
        overdue_now = sla.level(p.confirmed_at, p.sla_due_at, now, p.status not in ("fixed", "rejected")) == "overdue"
        p.priority_score, p.priority_components = priority.compute(
            severity=p.severity, road_class=p.road_class, device_count=p.device_count, opened_at=p.created_at, now=now,
            status=p.status, overdue=overdue_now)
        for r in reports:
            if r.pothole_id == p.pothole_id:
                r.status = p.status
    return potholes, reports, events


def offices_by_id(offices: dict[str, Office]) -> dict:
    return {o.office_id: o for o in offices.values()}


def synthetic(rng: random.Random, n: int, offices: dict[str, Office]) -> list[Pothole]:
    """Load-test points around Grand Tunis (no photos, no reports)."""
    now = datetime.now(timezone.utc)
    out = []
    for _ in range(n):
        created = now - timedelta(days=rng.uniform(0, 120))
        status = rng.choice(["new", "confirmed", "confirmed", "sheet_sent", "fixed", "fixed"])
        sev = rng.choice([1, 2, 3, 3, 4, 5])
        p = Pothole(pothole_id=uuid.uuid4(), status=status, lat=rng.uniform(36.72, 36.90), lon=rng.uniform(10.05, 10.33),
                    severity=sev, report_count=1, device_count=rng.randint(1, 4), target_office_id=offices["mun-tunis"].office_id,
                    region="Tunis", municipality="Tunis", road_class="urbain_secondaire", address_label="Point synthétique",
                    created_at=created, updated_at=created, confirmed_at=created if status != "new" else None,
                    fixed_at=min(created + timedelta(days=rng.uniform(1, 20)), now) if status == "fixed" else None,
                    priority_components={})
        p.priority_score, p.priority_components = priority.compute(
            severity=sev, road_class=p.road_class, device_count=p.device_count, opened_at=created, now=now, status=status)
        out.append(p)
    return out


async def main(extra: int) -> None:
    rng = random.Random(42)
    await migrate(engine)
    async with async_session() as db:
        await db.execute(text("TRUNCATE report_events, confirmations, jobs, feedback_labels, messages, reports, potholes CASCADE"))
        tokens = await upsert_offices(db, demo=True)
        await db.commit()
        offices = {o.code: o for o in (await db.execute(select(Office))).scalars()}
    potholes, reports, events = await build(rng, offices)
    async with async_session() as db:
        db.add_all(potholes)
        await db.flush()
        db.add_all(reports)
        db.add_all(events)
        if extra:
            db.add_all(synthetic(rng, extra, offices))
        now = datetime.now(timezone.utc)
        for device_id, thread in CONVERSATIONS.items():
            start = now - timedelta(days=rng.uniform(1, 12))
            for n, (sender, body) in enumerate(thread):
                db.add(Message(device_id=device_id, sender=sender, body=body, created_at=start + timedelta(minutes=37 * n)))
        await db.commit()
    print(f"Seeded {len(potholes)} potholes, {len(reports)} reports, {len(events)} events"
          + (f", {extra} synthetic potholes" if extra else "") + f", {len(CONVERSATIONS)} conversations.")
    print("Demo office logins (dashboard): " + ", ".join(f"{c}: {t}" for c, t in tokens.items() if c in ("mun-tunis", "dre-tunis", "ministry")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extra", type=int, default=0, help="synthetic potholes for load tests (e.g. 5000)")
    asyncio.run(main(parser.parse_args().extra))

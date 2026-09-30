"""GET /stats and POST /assistant for the authorities dashboard."""

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.db_models import Report
from backend.app.insights import OPEN, compute_stats, latest_per_pothole, summarize_all
from backend.app.rag_client import chat as rag_chat
from backend.app.schemas import AssistantReply, AssistantRequest

router = APIRouter(tags=["insights"])

STATUS_FR = {"new": "nouveau", "confirmed": "confirmé", "sheet_sent": "fiche envoyée", "fixed": "réparé", "rejected": "rejeté"}

# ponytail: MVP repair playbook in the prompt; move it into the RAG rule base
# once sourced engineering rules replace the placeholders (SCRUM-21).
PLAYBOOK = """Méthode de réparation selon la sévérité (règles MVP, à valider par les services techniques) :
- Sévérité 1-2 : surveillance ; colmatage à l'enrobé à froid lors de la prochaine tournée.
- Sévérité 3 : réparation à l'enrobé à chaud sous 14 j : découpe rectangulaire à bords francs, nettoyage, couche d'accrochage (émulsion), remplissage par couches, compactage.
- Sévérité 4-5 : balisage immédiat (cônes, ruban, signalisation de nuit), puis réparation définitive sous 48 h (5) ou 7 j (4) : découpe à la scie, purge des matériaux dégradés, reprise de la fondation si elle est atteinte, enrobé à chaud compacté, joints scellés."""


async def _summaries(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(Report).order_by(Report.created_at.desc()))).scalars()
    return summarize_all(list(rows))


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)) -> dict:
    return compute_stats(await _summaries(db))


# The playbook per pothole, so the LLM copies the method instead of mapping
# severity to method itself (Llama-8B got that wrong).
METHOD = {
    1: "surveillance, colmatage à froid",
    2: "surveillance, colmatage à froid",
    3: "enrobé à chaud sous 14 j",
    4: "balisage immédiat + réparation définitive sous 7 j",
    5: "balisage immédiat + réparation définitive sous 48 h",
}


def _line(p: dict, now: datetime) -> str:
    age = (now - p["created_at"]).days
    due = " | ÉCHÉANCE DÉPASSÉE" if p["overdue"] else ""
    return (
        f"{p['ref']} | sévérité {p['score'] or '?'} /5 | {STATUS_FR[p['status'].value]} | "
        f"{p['address'] or 'adresse inconnue'} | GPS {p['lat']:.5f}, {p['lon']:.5f} | "
        f"{p['cluster_size']} signalement(s) | il y a {age} j | {p['target_office'] or 'non attribué'} | méthode : {METHOD.get(p['score'], 'inspection sur place')}{due}"
    )


def _fallback(s: dict, top: list[dict], now: datetime) -> str:
    lines = [
        "Le modèle de langage est momentanément indisponible ; voici l'état actuel à partir des données :",
        f"- {s['open']} nids-de-poule ouverts, dont {s['urgent_open']} urgents (sévérité ≥ 4) et {s['overdue']} en retard.",
        f"- {s['fixed']} réparés ; délai médian de réparation : {s['median_repair_days'] or '—'} j.",
        "Les plus prioritaires :",
    ]
    lines += [f"- {_line(p, now)}" for p in top[:5]]
    return "\n".join(lines)


@router.post("/assistant", response_model=AssistantReply)
async def assistant(body: AssistantRequest, db: AsyncSession = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    summaries = await _summaries(db)
    s = compute_stats(summaries)
    potholes = latest_per_pothole(summaries)
    open_ = sorted((p for p in potholes if p["status"] in OPEN), key=lambda p: p["priority"], reverse=True)

    data = "\n".join(_line(p, now) for p in open_[:80])
    history = "\n".join(f"{'Agent' if t.role == 'user' else 'Assistant'} : {t.content}" for t in body.history[-6:])
    prompt = f"""Tu es « Sabeel Assist », l'assistant des services techniques (municipalité, DGPC) de Sabeel, la plateforme tunisienne de signalement des nids-de-poule.
Réponds dans la langue de la question (français, arabe ou anglais), de façon concise, structurée et opérationnelle.
Règles strictes :
- Utilise UNIQUEMENT les données ci-dessous pour les chiffres, lieux et statuts. N'invente jamais un nid-de-poule, une adresse ou un chiffre. Si l'information manque, dis-le.
- Quand tu cites un nid-de-poule, donne sa référence exacte (ex. TN-A1B2), son adresse et ses coordonnées GPS.
- Pour les conseils de réparation, suis la méthode ci-dessous selon la sévérité.

{PLAYBOOK}

Statistiques au {now:%d/%m/%Y} : {s['potholes_total']} nids-de-poule suivis ({s['reports_total']} signalements citoyens) ; {s['open']} ouverts dont {s['urgent_open']} urgents et {s['overdue']} en retard ; {s['fixed']} réparés ; {s['rejected']} rejetés (faux positifs) ; délai médian de réparation {s['median_repair_days'] or '—'} j ; répartition par bureau {s['by_office']} ; quartiers les plus touchés {s['top_zones']}.

Nids-de-poule ouverts, du plus prioritaire au moins prioritaire (référence | sévérité | statut | adresse | GPS | nb de signalements | âge | bureau | méthode de réparation à citer telle quelle) :
{data}

{history}
Agent : {body.question}
Assistant :"""

    answer = await rag_chat(prompt)
    source = "llm" if answer else "fallback"
    if not answer:
        answer = _fallback(s, open_, now)

    by_ref = {p["ref"]: p for p in potholes}
    cited = dict.fromkeys(re.findall(r"TN-[0-9A-Z]{4}", answer))
    refs = [by_ref[r] for r in cited if r in by_ref]
    return {"answer": answer.strip(), "refs": refs, "source": source}

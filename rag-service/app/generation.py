"""LLM call (Hugging Face Inference API) and the never-fabricates template fallback."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from . import config

logger = logging.getLogger(__name__)

# huggingface_hub's own `timeout=` kwarg does not reliably bound
# chat_completion() against the router endpoint in practice (observed
# hanging well past the configured value during Sprint 1 testing) -- a
# thread-pool wall-clock timeout is used instead as the real, unbypassable
# bound. The orphaned call is left to finish in the background thread; its
# result is simply never awaited past the deadline.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="hf-llm-call")

_OFFICE_LABELS = {
    "Municipality": "la Municipalité (Baladiya)",
    "DGPC": "la DGPC (Direction Générale des Ponts et Chaussées)",
    "Ministry of Equipment": "le Ministère de l'Équipement, de l'Habitat et de l'Aménagement du Territoire",
}


def build_prompt(
    chunks: list[dict], score: int, road_type: str, lat: float, lon: float,
    office_name: str | None = None, address: str | None = None,
) -> str:
    context_lines = []
    for chunk in chunks:
        meta = chunk["metadata"]
        context_lines.append(f"[{meta['rule_id']}] ({meta['source']}): {chunk['document']}")
    context_block = "\n".join(context_lines)

    return f"""Tu es un assistant qui rédige des fiches de travaux pour la voirie tunisienne.

Un nid de poule a été signalé et confirmé :
- Sévérité : {score}/5
- Type de route : {road_type}
- Position : {lat}, {lon}{f" ({address})" if address else ""}
- Bureau destinataire : {office_name or "à déterminer selon les règles"}

Règles disponibles (cite UNIQUEMENT ces identifiants, n'invente jamais un identifiant qui n'est pas dans cette liste) :
{context_block}

Rédige une fiche de travaux courte (5-8 lignes) en français : nature du problème, gravité, méthode de réparation recommandée (d'après les règles techniques ci-dessus), signalisation, bureau responsable et base légale. Écris en texte brut, sans markdown (pas d'astérisques ni de titres). Si aucune règle ci-dessus ne s'applique clairement, dis-le explicitement.

Termine ta réponse par une ligne exacte au format :
Références: ID1, ID2
en listant uniquement les identifiants des règles ci-dessus que tu as réellement utilisées.
"""


def _do_chat_completion(prompt: str, timeout_s: float, model: str, max_tokens: int) -> str:
    if config.LLM_BASE_URL:  # OpenAI-compatible provider (Groq, OpenRouter, ...)
        client = InferenceClient(base_url=config.LLM_BASE_URL, api_key=config.HF_API_TOKEN, timeout=timeout_s)
        response = client.chat_completion(
            model=model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    client = InferenceClient(model=model, token=config.HF_API_TOKEN, timeout=timeout_s)
    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


class LLMRateLimited(Exception):
    """The provider's per-minute quota is used up; try again after `retry_after_s`."""

    def __init__(self, retry_after_s: float):
        super().__init__(f"LLM rate-limited, retry after {retry_after_s:.0f} s")
        self.retry_after_s = retry_after_s


def _retry_after(exc: Exception) -> float:
    headers = getattr(getattr(exc, "response", None), "headers", None) or {}
    try:
        return float(headers.get("retry-after", 30))
    except (TypeError, ValueError):
        return 30.0


def call_llm(
    prompt: str,
    timeout_s: float | None = None,
    model: str | None = None,
    max_tokens: int = 400,
) -> str | None:
    """Single attempt against the primary model, bounded by a real wall-clock
    timeout (see module docstring -- huggingface_hub's own timeout kwarg is
    not trusted). Never chains multiple models at runtime. Returns None on
    any failure or timeout -- caller must fall back to the template.
    """
    if not config.HF_API_TOKEN:
        logger.warning("No HF_API_TOKEN configured; skipping LLM call.")
        return None

    timeout_s = timeout_s or config.LLM_TIMEOUT_S

    future = _executor.submit(_do_chat_completion, prompt, timeout_s, model or config.HF_MODEL_PRIMARY, max_tokens)
    try:
        return future.result(timeout=timeout_s)
    except FutureTimeoutError:
        logger.warning("HF Inference API call exceeded %.1fs wall-clock timeout; falling back.", timeout_s)
        return None
    except HfHubHTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 429:
            raise LLMRateLimited(_retry_after(exc)) from exc
        logger.warning("HF Inference API call failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - any failure must fall back cleanly
        logger.warning("HF Inference API call failed: %s", exc)
        return None


def pick_target_office(chunks: list[dict]) -> str:
    """The office named by the best-ranked jurisdiction rule (method rules say "any")."""
    for chunk in chunks:
        office = chunk["metadata"].get("target_office")
        if office in config.TARGET_OFFICES:
            return office
    return "Municipality"


OFFICE_LABELS_FR = {
    "Municipality": "Municipalité",
    "DGPC": "Direction Générale des Ponts et Chaussées (DGPC)",
    "Ministry of Equipment": "Ministère de l'Équipement",
}


SEVERITY_FR = {1: "faible", 2: "faible", 3: "moyenne", 4: "élevée", 5: "dangereuse"}


def _first(chunks: list[dict], prefixes: tuple[str, ...]) -> dict | None:
    return next((c for c in chunks if c["metadata"]["rule_id"].startswith(prefixes)), None)


def render_template_fallback(
    chunks: list[dict], score: int, road_type: str, lat: float, lon: float, target_office: str,
    office_name: str | None = None,
) -> str:
    """Deterministic sheet that cannot fabricate: every sentence below either
    comes from the request or is a retrieved rule's own text. Used whenever
    the LLM is unavailable or fails citation validation."""
    office_label = office_name or _OFFICE_LABELS.get(target_office, target_office)

    if not chunks:
        return (
            f"Nid de poule signalé (sévérité {score}/5) sur route de type '{road_type}' "
            f"({lat:.5f}, {lon:.5f}).\n"
            "Aucune règle suffisamment pertinente trouvée dans la base actuelle — "
            "vérification manuelle recommandée.\n"
            f"Transmis à : {office_label}."
        )

    law = next((c for c in chunks if c["metadata"].get("target_office") in config.TARGET_OFFICES), None)
    method = _first(chunks, ("FHWA-99-168-S3.2.2",) if score >= 3 else ("FHWA-99-168-S3.2.1",)) or _first(
        chunks, ("FHWA-99-168-S3.2",))
    signage = _first(chunks, ("FHWA-99-168-S4.1",))
    urgency = _first(chunks, ("FHWA-99-168-S2",))
    used = [c for c in (law, method, signage, urgency) if c] or chunks

    def body(c: dict) -> str:
        return " ".join(c["document"].split())

    lines = [
        f"FICHE DE TRAVAUX — nid-de-poule confirmé, gravité {score}/5 ({SEVERITY_FR.get(score, '?')}).",
        f"Localisation : {lat:.5f}, {lon:.5f} — route de type « {road_type} ».",
        f"Destinataire : {office_label}.",
    ]
    if law:
        lines.append(f"Compétence [{law['metadata']['rule_id']}] : {body(law)}")
    if urgency and score >= 4:
        lines.append(f"Urgence [{urgency['metadata']['rule_id']}] : {body(urgency)}")
    if method:
        lines.append(f"Méthode [{method['metadata']['rule_id']}] : {body(method)}")
    if signage:
        lines.append(f"Signalisation [{signage['metadata']['rule_id']}] : {body(signage)}")
    if not (law or method):
        lines += [f"- [{c['metadata']['rule_id']}] {c['metadata']['source']} : {body(c)[:300]}" for c in chunks]
    lines.append("Fiche générée à partir des règles citées (rédaction automatique indisponible) — à relire avant approbation.")
    lines.append("Références: " + ", ".join(c["metadata"]["rule_id"] for c in used))
    return "\n".join(lines)

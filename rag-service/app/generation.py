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


def build_prompt(chunks: list[dict], score: int, road_type: str, lat: float, lon: float) -> str:
    context_lines = []
    for chunk in chunks:
        meta = chunk["metadata"]
        context_lines.append(f"[{meta['rule_id']}] ({meta['source']}): {chunk['document']}")
    context_block = "\n".join(context_lines)

    return f"""Tu es un assistant qui rédige des fiches de travaux pour la voirie tunisienne.

Un nid de poule a été signalé et confirmé :
- Sévérité : {score}/5
- Type de route : {road_type}
- Position : {lat}, {lon}

Règles disponibles (cite UNIQUEMENT ces identifiants, n'invente jamais un identifiant qui n'est pas dans cette liste) :
{context_block}

Rédige une fiche de travaux courte (5-8 lignes) en français : nature du problème, gravité, action recommandée, bureau responsable. Si aucune règle ci-dessus ne s'applique clairement, dis-le explicitement.

Termine ta réponse par une ligne exacte au format :
Références: ID1, ID2
en listant uniquement les identifiants des règles ci-dessus que tu as réellement utilisées.
"""


def _do_chat_completion(prompt: str, timeout_s: float, model: str, max_tokens: int) -> str:
    client = InferenceClient(model=model, token=config.HF_API_TOKEN, timeout=timeout_s)
    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


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
        logger.warning("HF Inference API call failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 - any failure must fall back cleanly
        logger.warning("HF Inference API call failed: %s", exc)
        return None


def pick_target_office(chunks: list[dict]) -> str:
    if not chunks:
        return "Municipality"
    top = chunks[0]["metadata"]
    office = top.get("target_office", "Municipality")
    return office if office in config.TARGET_OFFICES else "Municipality"


def render_template_fallback(
    chunks: list[dict], score: int, road_type: str, lat: float, lon: float, target_office: str
) -> str:
    """Deterministic, structurally-cannot-fabricate sheet: stitches real
    retrieved excerpts directly. Used whenever the LLM path fails or fails
    citation validation, and as the direct path when no rules match at all.
    """
    office_label = _OFFICE_LABELS.get(target_office, target_office)

    if not chunks:
        return (
            f"Nid de poule signalé (sévérité {score}/5) sur route de type '{road_type}' "
            f"({lat:.5f}, {lon:.5f}).\n"
            "Aucune règle suffisamment pertinente trouvée dans la base actuelle — "
            "vérification manuelle recommandée.\n"
            f"Transmis à : {office_label}."
        )

    lines = [
        f"Nid de poule confirmé — sévérité {score}/5, route de type '{road_type}'.",
        f"Position : {lat:.5f}, {lon:.5f}.",
        "Règles applicables :",
    ]
    for chunk in chunks:
        meta = chunk["metadata"]
        excerpt = chunk["document"][:200]
        lines.append(f"- [{meta['rule_id']}] {meta['source']} : {excerpt}")
    lines.append(f"Action recommandée : intervention à programmer selon les règles ci-dessus.")
    lines.append(f"Transmis à : {office_label}.")
    ref_ids = ", ".join(c["metadata"]["rule_id"] for c in chunks)
    lines.append(f"Références: {ref_ids}")
    return "\n".join(lines)

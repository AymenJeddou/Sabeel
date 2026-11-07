"""No-network tests: mocks retrieval and the LLM call so these run in CI
without a Chroma index or an HF token."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import pipeline  # noqa: E402


def _chunk(rule_id: str, road_type: str = "urbain_principal", target_office: str = "Municipality") -> dict:
    return {
        "id": rule_id,
        "document": f"Texte de la règle {rule_id}.",
        "metadata": {
            "rule_id": rule_id,
            "source": f"Source {rule_id}",
            "road_type": road_type,
            "target_office": target_office,
            "is_placeholder": True,
        },
        "similarity": 0.9,
    }


def test_generate_insufficient_rules_path(monkeypatch):
    monkeypatch.setattr(pipeline, "retrieve_chunks", lambda road_type, score, top_k=None, jurisdiction=None: [])

    result = pipeline.generate(lat=36.8, lon=10.18, score=4, road_type="urbain_principal")

    assert result["rule_citations"] == []
    assert result["target_office"] == "Municipality"
    assert "manuelle" in result["sheet_text"].lower() or "vérification" in result["sheet_text"].lower()
    assert result["road_type"] == "urbain_principal"


def test_generate_falls_back_to_template_when_llm_unavailable(monkeypatch):
    chunks = [_chunk("RULE_A", target_office="DGPC")]
    monkeypatch.setattr(pipeline, "retrieve_chunks", lambda road_type, score, top_k=None, jurisdiction=None: chunks)
    monkeypatch.setattr(pipeline, "call_llm", lambda prompt: None)

    result = pipeline.generate(lat=36.8, lon=10.18, score=4, road_type="rural")

    assert result["target_office"] == "DGPC"
    assert len(result["rule_citations"]) == 1
    assert result["rule_citations"][0]["rule_id"] == "RULE_A"
    assert "RULE_A" in result["sheet_text"]


def test_generate_discards_llm_output_with_invented_citation(monkeypatch):
    chunks = [_chunk("RULE_A")]
    monkeypatch.setattr(pipeline, "retrieve_chunks", lambda road_type, score, top_k=None, jurisdiction=None: chunks)
    monkeypatch.setattr(
        pipeline, "call_llm", lambda prompt: "Some sheet text.\nRéférences: RULE_A, RULE_INVENTED"
    )

    result = pipeline.generate(lat=36.8, lon=10.18, score=4, road_type="urbain_principal")

    # Invalid citation -> whole LLM output discarded -> template fallback used instead.
    assert result["rule_citations"] == [{"rule_id": "RULE_A", "source": "Source RULE_A", "excerpt": "Texte de la règle RULE_A."}]
    assert "RULE_INVENTED" not in result["sheet_text"]


def test_generate_never_raises_on_internal_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(pipeline, "retrieve_chunks", boom)

    result = pipeline.generate(lat=36.8, lon=10.18, score=4, road_type="urbain_principal")

    assert result["rule_citations"] == []
    assert result["target_office"] == "Municipality"
    assert result["generation_ms"] >= 0


def test_rate_limited_llm_gives_a_template_flagged_for_retry(monkeypatch):
    from app.generation import LLMRateLimited

    def limited(prompt):
        raise LLMRateLimited(17)

    monkeypatch.setattr(pipeline, "retrieve_chunks", lambda road_type, score, top_k=None, jurisdiction=None: [_chunk("RULE_A")])
    monkeypatch.setattr(pipeline, "call_llm", limited)

    result = pipeline.generate(lat=36.8, lon=10.18, score=4, road_type="urbain_principal")

    assert result["retry_after_s"] == 17 and result["llm_used"] is False
    assert "RULE_A" in result["sheet_text"]

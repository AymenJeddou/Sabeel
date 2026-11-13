import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.citation_guard import extract_claimed_ids, validate_citations  # noqa: E402


def _chunk(rule_id: str) -> dict:
    return {"metadata": {"rule_id": rule_id, "source": f"src-{rule_id}"}, "document": f"text-{rule_id}"}


def test_extract_claimed_ids_parses_trailer():
    text = "Some sheet body.\nRéférences: RULE_A, RULE_B"
    assert extract_claimed_ids(text) == ["RULE_A", "RULE_B"]


def test_extract_claimed_ids_returns_none_without_trailer():
    assert extract_claimed_ids("Some sheet body with no trailer.") is None


def test_validate_citations_accepts_valid_ids():
    allowlist = [_chunk("RULE_A"), _chunk("RULE_B")]
    text = "Body.\nRéférences: RULE_A"
    validated_text, matched = validate_citations(text, allowlist)
    assert validated_text == text
    assert len(matched) == 1
    assert matched[0]["metadata"]["rule_id"] == "RULE_A"


def test_validate_citations_rejects_id_outside_allowlist():
    allowlist = [_chunk("RULE_A")]
    text = "Body.\nRéférences: RULE_A, RULE_INVENTED"
    validated_text, matched = validate_citations(text, allowlist)
    assert validated_text is None
    assert matched == []


def test_validate_citations_rejects_missing_trailer():
    allowlist = [_chunk("RULE_A")]
    validated_text, matched = validate_citations("Body with no references line.", allowlist)
    assert validated_text is None
    assert matched == []


def test_trailer_is_the_last_reference_line_and_markdown_is_ignored():
    text = "Selon la Référence : art. 3 de la loi...\n\n**Références** : `R1`, `R2`; R1."
    assert extract_claimed_ids(text) == ["R1", "R2"]

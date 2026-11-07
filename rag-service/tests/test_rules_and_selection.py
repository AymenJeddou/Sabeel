"""The rule corpus and the shown-chunk selection, without Chroma or an LLM."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.generation import render_template_fallback  # noqa: E402
from app.pipeline import select_shown  # noqa: E402
from ingestion.build_index import load_rule_files  # noqa: E402

RULES = Path(__file__).resolve().parent.parent / "rules_real"


def test_no_placeholder_rule_is_left():
    chunks = load_rule_files()
    assert chunks and not any(c["metadata"]["is_placeholder"] for c in chunks)
    assert not any(c["metadata"]["rule_id"].startswith("PH-") for c in chunks)


def test_every_rule_has_a_source_and_a_valid_scope():
    for path in RULES.glob("*.yaml"):
        for rule in yaml.safe_load(path.read_text(encoding="utf-8"))["rules"]:
            assert rule["source"] and rule["text"].strip(), rule["rule_id"]
            assert rule["road_type"] in config.ROAD_TYPES + ["all"], rule["rule_id"]
            assert rule["target_office"] in config.TARGET_OFFICES + ["any"], rule["rule_id"]


def test_jurisdiction_metadata_follows_the_office():
    by_id = {c["metadata"]["rule_id"]: c["metadata"] for c in load_rule_files()}
    assert by_id["TN-CCL2018-ART69"]["jurisdiction"] == "municipal"
    assert by_id["TN-LOI86-17-RN"]["jurisdiction"] == "state"
    assert by_id["FHWA-99-168-S3.2.2"]["jurisdiction"] == "any"


def _c(rule_id, office="any", sim=0.5):
    return {"id": rule_id, "document": f"Texte {rule_id}.", "similarity": sim,
            "metadata": {"rule_id": rule_id, "source": f"Source {rule_id}", "target_office": office}}


def test_selection_always_keeps_the_law_and_the_right_method():
    ranked = [_c("FHWA-99-168-S4.1", sim=0.7), _c("FHWA-99-168-S2", sim=0.67), _c("FHWA-99-168-S3.2.1", sim=0.6),
              _c("FHWA-99-168-S1.1", sim=0.55), _c("FHWA-99-168-S3.2.2", sim=0.5), _c("TN-CCL2018-ART69", "Municipality", 0.4)]
    ids = [c["metadata"]["rule_id"] for c in select_shown(ranked, 4, 4)]
    assert "TN-CCL2018-ART69" in ids and "FHWA-99-168-S3.2.2" in ids and len(ids) == 4
    small = [c["metadata"]["rule_id"] for c in select_shown(ranked, 2, 3)]
    assert "FHWA-99-168-S3.2.1" in small


def test_template_names_office_law_method_and_cites_only_shown_rules():
    shown = [_c("TN-CCL2018-ART69", "Municipality"), _c("FHWA-99-168-S3.2.2"), _c("FHWA-99-168-S4.1")]
    text = render_template_fallback(shown, 4, "urbain_principal", 36.8, 10.18, "Municipality", "Municipalité de Tunis")
    assert "Municipalité de Tunis" in text and "Méthode [FHWA-99-168-S3.2.2]" in text
    refs = text.rsplit("Références:", 1)[1]
    assert {r.strip() for r in refs.split(",")} <= {"TN-CCL2018-ART69", "FHWA-99-168-S3.2.2", "FHWA-99-168-S4.1"}

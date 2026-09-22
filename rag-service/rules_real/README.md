# Real sourced rules

Every file here must carry, per entry (see `loi_2018_29_ccl.yaml` and `loi_86_17_classification.yaml` for working examples):

- `rule_id` — stable, unique slug (e.g. `TN-CCL2018-ART69`)
- `text` — the rule content used for retrieval/citation (verbatim quote where available; otherwise a clearly-scoped paraphrase — say so in `note`)
- `source` — full legal citation: law/decree number, date, official title, article number
- `road_type` — one of `urbain_principal`, `urbain_secondaire`, `rural`, `autoroute`, `piste`
- `target_office` — one of `Municipality`, `DGPC`, `Ministry of Equipment`
- `severity_min` — score (1-5) this rule starts applying at
- `note` (optional) — anything about provenance/verification status worth flagging (e.g. "verbatim via secondary legal database, not yet cross-checked against the primary PDF")

At the file level: `doc_title` and `is_placeholder: false`.

Sourcing research done for Sprint 1 (2026-09-19/20) via live web search — see the Sprint 1 plan for the full research trail. Two real, verifiable primary sources were found and are seeded here:

1. *Loi organique n°2018-29 du 9 mai 2018, relative au Code des Collectivités Locales*, Article 69 — municipal road domain.
2. *Loi n°86-17 du 7 mars 1986, portant refonte de la législation relative au domaine public routier de l'État* — RN/RR/RL classification — plus the DGPC's mandate as described on mehat.gov.tn (Ministère de l'Équipement et de l'Habitat).

**Known gap**: the primary PDF of Loi 2018-29 (faolex.fao.org/docs/pdf/tun202128.pdf) could not be text-extracted in this session (no local PDF-to-text tool available). The Article 69 quote came via a secondary legal-database site's presentation of the law — reasonable for an MVP, but should be cross-checked against the primary PDF before this is used for anything beyond a demo. The RN/RR/RL definitions in `loi_86_17_classification.yaml` are paraphrased from a secondary summary, not verbatim article text — the law's number/date/title is confirmed, the definition wording is not yet verified against primary text.

# Sample `generate()` calls

## curl (service running on :8001)

```bash
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"lat": 36.8065, "lon": 10.1815, "score": 4, "road_type": "urbain_principal"}'
```

```bash
curl http://localhost:8001/health
```

## Hand-written example (Sprint 1 DoD requirement)

Input: `{"lat": 36.8065, "lon": 10.1815, "score": 4, "road_type": "urbain_principal"}` (a point in central Tunis).

Expected retrieval: `TN-CCL2018-ART69` (real, municipal domain) plus `PH-URB-PRIN-002`/`PH-URB-PRIN-003` (placeholder, repair method + signage) as the top matches for `urbain_principal` at severity 4.

Expected `generate()` output shape (LLM-generated `sheet_text` will vary in wording; the template-fallback path produces something close to this):

```json
{
  "sheet_text": "Nid de poule confirmé — sévérité 4/5, route de type 'urbain_principal'.\nPosition : 36.80650, 10.18150.\nRègles applicables :\n- [TN-CCL2018-ART69] Loi organique n°2018-29 du 9 mai 2018, relative au Code des Collectivités Locales, Article 69 : L'article 69 du Code des Collectivités Locales inclut dans le domaine public communal...\n- [PH-URB-PRIN-002] MVP engineering placeholder (not a real statute) : Pour un nid de poule de sévérité 3 ou 4 sur chaussée urbaine principale...\nAction recommandée : intervention à programmer selon les règles ci-dessus.\nTransmis à : la Municipalité (Baladiya).\nRéférences: TN-CCL2018-ART69, PH-URB-PRIN-002",
  "rule_citations": [
    {"rule_id": "TN-CCL2018-ART69", "source": "Loi organique n°2018-29 du 9 mai 2018, relative au Code des Collectivités Locales, Article 69", "excerpt": "L'article 69 du Code des Collectivités Locales inclut dans le domaine public communal..."},
    {"rule_id": "PH-URB-PRIN-002", "source": "MVP engineering placeholder (not a real statute)", "excerpt": "Pour un nid de poule de sévérité 3 ou 4 sur chaussée urbaine principale..."}
  ],
  "target_office": "Municipality",
  "road_type": "urbain_principal",
  "generated_at": "2026-09-20T10:00:00Z",
  "generation_ms": 842.5
}
```

Note `target_office: "Municipality"` traces directly back to `TN-CCL2018-ART69`'s real citation (Article 69 excludes national roads/autoroutes from municipal domain, so anything in `urbain_principal`/`urbain_secondaire` routes to the Municipality) — this is the actually-sourced part of the pipeline, not a placeholder guess.

## Insufficient-rules example

Input: `{"lat": 0.0, "lon": 0.0, "score": 3, "road_type": "autoroute"}` with an empty/mismatched index (or any query that produces no chunk above the similarity floor):

```json
{
  "sheet_text": "Nid de poule signalé (sévérité 3/5) sur route de type 'autoroute' (0.00000, 0.00000).\nAucune règle suffisamment pertinente trouvée dans la base actuelle — vérification manuelle recommandée.\nTransmis à : la Municipalité (Baladiya).",
  "rule_citations": [],
  "target_office": "Municipality",
  "road_type": "autoroute",
  "generated_at": "2026-09-20T10:00:00Z",
  "generation_ms": 120.0
}
```

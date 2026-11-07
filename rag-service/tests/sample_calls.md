# Sample call (template path, recorded 2026-11-07)

```bash
curl -X POST localhost:8001/generate -H "Content-Type: application/json" \
  -d '{"lat":36.8012,"lon":10.1863,"score":4,"road_type":"urbain_principal",
       "office_name":"Municipalité de Tunis","address":"Avenue Mohamed V, Tunis","jurisdiction":"municipal"}'
```

Retrieved (best first): `FHWA-99-168-S4.1` 0.70, `FHWA-99-168-S2` 0.67,
`TN-CCL2018-ART69` 0.64, `FHWA-99-168-S3.2.1` 0.51, `FHWA-99-168-S3.2.2` 0.50.
Shown to the LLM: the law (`TN-CCL2018-ART69`), the method that fits
severity 4 (`FHWA-99-168-S3.2.2`, semi-permanent) and the two best others.

With the LLM unavailable, the sheet is:

```
FICHE DE TRAVAUX — nid-de-poule confirmé, gravité 4/5 (élevée).
Localisation : 36.80120, 10.18630 — route de type « urbain_principal ».
Destinataire : Municipalité de Tunis.
Compétence [TN-CCL2018-ART69] : L'article 69 du Code des Collectivités Locales inclut dans le domaine public communal : ...
Urgence [FHWA-99-168-S2] : ... Une administration routière doit réparer les nids-de-poule potentiellement dangereux dès qu'elle en a connaissance. ...
Méthode [FHWA-99-168-S3.2.2] : Réparation semi-permanente ... 1. évacuer l'eau et les débris ; 2. découper les bords ... ; 3. mettre en place l'enrobé ; 4. compacter ... ; 5. rouvrir à la circulation ...
Signalisation [FHWA-99-168-S4.1] : Toute opération de colmatage de nid-de-poule doit s'accompagner d'une signalisation ...
Fiche générée à partir des règles citées (rédaction automatique indisponible) — à relire avant approbation.
Références: TN-CCL2018-ART69, FHWA-99-168-S3.2.2, FHWA-99-168-S4.1, FHWA-99-168-S2
```

For a national road (`"jurisdiction":"state"`, e.g. Avenue Habib Bourguiba,
tagged RN9), the municipal rule is filtered out and `TN-LOI86-17-RN-URBAIN`
names the regional directorate of equipment instead.

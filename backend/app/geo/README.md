# OSM enrichment

`enrichment.py` turns a pothole's GPS point into a road class, road reference,
street, governorate and municipality with one Nominatim reverse-geocoding
call (zoom 17 = the nearest street, with `namedetails` for the `ref` tag),
then routes the pothole to an office:

| Road class (from `road_class_map.py`) | Office |
|---|---|
| `national` (ref RN… / GP… / P…), `regional` (RR… / C… / MC…) | Regional directorate of equipment (DGPC) of the governorate (Law 86-17) |
| `autoroute` (A…) | Ministry (motorways are managed by Tunisie Autoroutes, out of MVP scope) |
| everything else | The municipality (Law 2018-29, art. 69) |

Answers are cached per ~30 m cell in `geo_cache`. Nominatim's usage policy is
respected (real User-Agent, at most one request per second, no bulk calls).
If OSM can't be reached, the Sprint 1 city-box heuristic and the nearest
seeded office are used, `enrichment_source` is `fallback`, and the job retries
later. A report never fails because of OSM.

Overpass was planned too (roadmap #24) but isn't needed: Nominatim already
returns the nearest way with its `highway` type and `ref`, and the public
Overpass servers reject requests from some networks.

## Verification on 20 real points

Recorded on 2026-11-07 with `python -m backend.app.scripts.record_osm_fixtures`.
The raw answers are the test fixtures (`tests/fixtures/osm_points.json`), so CI
replays them without network.

| Point | Expected office | Result | Ref | Street | Municipality | Governorate |
|---|---|---|---|---|---|---|
| RN1 at Radès | DGPC | national → DGPC ✅ | RN1 | Route Nationale Tunis - Ras Jedir | Radès | Ben Arous |
| RN9 at La Marsa | DGPC | national → DGPC ✅ | RN9 | Route Nationale Tunis - La Marsa | Tunis | Tunis |
| Avenue Habib Bourguiba, Tunis | DGPC | national → DGPC ✅ | RN9 | Avenue Habib Bourguiba | Tunis | Tunis |
| Avenue Mohamed V, Tunis | Municipality | urbain_principal → Municipality ✅ | | Avenue Mohamed V | Tunis | Tunis |
| Rue de Marseille, Tunis | Municipality | urbain_secondaire → Municipality ✅ | | Rue de Marseille | Tunis | Tunis |
| Avenue de la Liberté, Tunis | Municipality | urbain_secondaire → Municipality ✅ | | Avenue de la Liberté | Tunis | Tunis |
| Avenue Habib Bourguiba, La Marsa | Municipality | urbain_secondaire → Municipality ✅ | | Avenue Habib Bourguiba | Tunis | Tunis |
| Avenue Hédi Nouira, El Menzah | Municipality | urbain_principal → Municipality ✅ | | Avenue Hédi Nouira | | Ariana |
| Rue du Lac Léman, Berges du Lac | Municipality | urbain_secondaire → Municipality ✅ | | Rue du Lac Leman | Tunis | Tunis |
| Residential street, Ennasr | Municipality | urbain_secondaire → Municipality ✅ | | Rue de Kaboul | | Ariana |
| Sidi Bou Saïd village street | Municipality | urbain_secondaire → Municipality ✅ | | Rue Abou El Kacem Chebbi | Tunis | Tunis |
| Sousse centre | Municipality | urbain_secondaire → Municipality ✅ | | Boulevard Yahia Ibn Omar | Sousse | Sousse |
| Sfax centre | Municipality | urbain_secondaire → Municipality ✅ | | Escalier Dimassi | Sfax | Sfax |
| Avenue Habib Bourguiba, Bizerte | DGPC | national → DGPC ✅ | RN11 | Avenue Habib Bourguiba | Bizerte | Bizerte |
| Avenue Habib Bourguiba, Menzel Abderrahmen | Municipality | urbain_secondaire → Municipality ✅ | | Avenue Habib Bourguiba | Menzel Abderrahmane | Bizerte |
| RN3 near Bir Mcherga | DGPC | national → DGPC ✅ | RN3 | RN3 | | Zaghouan |
| A1 motorway near Bouficha | Ministry | autoroute → Ministry ✅ | A1 | Autoroute Tunis - Sousse - Sfax | | Sousse |
| RR74E near Testour | DGPC | regional → DGPC ✅ | RR 74E | RR 74E | | Béja |
| Farm track near Mornag | Municipality | rural → Municipality ✅ | | | | Ben Arous |
| Gabès centre | Municipality | rural → Municipality ✅ | | Avenue Mohamed Ali | | Gabès |

20 / 20 route to the expected kind of office.

**Finding.** Avenue Habib Bourguiba in central Tunis (and its namesake in
Bizerte) is tagged as a national road (RN9, RN11) in OSM. Law 2018-29 art. 69
excludes classified national roads from the municipal domain, so these
potholes go to the regional directorate, not the city. The first guess (the
municipality) was wrong; the law-based routing is right.

**Known limits.** Some municipalities are missing from Nominatim's answer
(Ariana, rural areas); routing then falls back to the nearest municipality
office within 20 km, else the regional directorate. Only the pilot offices
(Grand Tunis, Sousse, Sfax) exist in `scripts/offices_data.py`; add a row per
new municipality.

"""OSM `highway` tag + `ref` -> Sabeel road class, RAG road type and office kind.

Two vocabularies, on purpose:
- `road_class` (priority weight, routing): national | regional | local |
  urbain_principal | urbain_secondaire | rural | piste | autoroute
- `road_type` (the RAG rule corpus, frozen in Sprint 1): urbain_principal |
  urbain_secondaire | rural | autoroute | piste

Tunisian refs in OSM: national roads are tagged `RN1`, `RN 9` (older data:
`GP1`, `P1`); regional roads `RR21`, `C35` (older: `MC`); local roads `RL`.
Classified national and regional roads belong to the Ministry of Equipment
(DGPC and its regional directorates, Law 86-17); everything else inside a
municipality belongs to that municipality (Law 2018-29, art. 69).
"""
from __future__ import annotations

import re

_NATIONAL = re.compile(r"^\s*(RN|GP|N|P)\s?-?\d", re.I)
_REGIONAL = re.compile(r"^\s*(RR|MC|C|R)\s?-?\d", re.I)
_LOCAL = re.compile(r"^\s*RL\s?-?\d", re.I)

MAJOR = {"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link"}
MINOR = {"tertiary", "tertiary_link", "residential", "living_street", "unclassified", "service", "road", "pedestrian"}
TRACK = {"track", "path", "bridleway"}
MOTORWAY = {"motorway", "motorway_link"}


def classify(highway: str | None, ref: str | None, urban: bool) -> tuple[str, str]:
    """Returns (road_class, road_type)."""
    highway = (highway or "").lower()
    ref = ref or ""
    if highway in MOTORWAY or ref.upper().startswith("A"):
        return "autoroute", "autoroute"
    if highway in TRACK:
        return "piste", "piste"
    if _NATIONAL.match(ref):
        return "national", "urbain_principal" if urban else "rural"
    if _REGIONAL.match(ref):
        return "regional", "urbain_principal" if urban else "rural"
    if _LOCAL.match(ref):
        return "local", "urbain_secondaire" if urban else "rural"
    if highway in MAJOR:
        return ("urbain_principal", "urbain_principal") if urban else ("regional", "rural")
    if highway in MINOR:
        return ("urbain_secondaire", "urbain_secondaire") if urban else ("rural", "rural")
    return ("urbain_secondaire", "urbain_secondaire") if urban else ("rural", "rural")


def office_kind_for(road_class: str) -> str:
    """Which kind of office repairs this road."""
    if road_class in ("national", "regional"):
        return "DGPC"
    if road_class == "autoroute":
        return "Ministry of Equipment"  # motorways are out of MVP scope (Tunisie Autoroutes)
    return "Municipality"

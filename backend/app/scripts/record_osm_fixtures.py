"""Records real Nominatim answers for the 20-point verification set
(issue #24) into backend/app/tests/fixtures/osm_points.json and prints the
expected-vs-actual table for backend/app/geo/README.md.

    python -m backend.app.scripts.record_osm_fixtures     (needs network)

Respects Nominatim's usage policy: one request per second, a real
User-Agent, 20 requests in total.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from backend.app.config import settings
from backend.app.geo.enrichment import parse
from backend.app.geo.road_class_map import office_kind_for

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "osm_points.json"

# (name, lat, lon, expected road_class, expected office kind)
POINTS = [
    ("RN1 at Radès", 36.753441, 10.249427, "national", "DGPC"),
    ("RN9 at La Marsa", 36.875413, 10.323792, "national", "DGPC"),
    ("Avenue Habib Bourguiba, Tunis (tagged RN9)", 36.800537, 10.187926, "national", "DGPC"),
    ("Avenue Mohamed V, Tunis", 36.801232, 10.186305, "urbain_principal", "Municipality"),
    ("Rue de Marseille, Tunis", 36.803750, 10.181782, "urbain_secondaire", "Municipality"),
    ("Avenue de la Liberté, Tunis", 36.805311, 10.150100, "urbain_principal", "Municipality"),
    ("Avenue Habib Bourguiba, La Marsa", 36.864390, 10.310499, "urbain_principal", "Municipality"),
    ("Avenue Hédi Nouira, El Menzah", 36.855860, 10.159110, "urbain_principal", "Municipality"),
    ("Rue du Lac Léman, Berges du Lac", 36.840480, 10.244134, "urbain_secondaire", "Municipality"),
    ("Residential street, Ennasr", 36.856500, 10.163000, "urbain_secondaire", "Municipality"),
    ("Sidi Bou Saïd village street", 36.870600, 10.341200, "urbain_secondaire", "Municipality"),
    ("Avenue Habib Bourguiba, Sousse", 35.828300, 10.637200, "urbain_principal", "Municipality"),
    ("Avenue Hédi Chaker, Sfax", 34.737900, 10.760000, "urbain_principal", "Municipality"),
    ("Avenue Habib Bourguiba, Bizerte (RN11)", 37.2681664, 9.8618981, "national", "DGPC"),
    ("Avenue Habib Bourguiba, Menzel Abderrahmen", 37.2369568, 9.8627493, "urbain_secondaire", "Municipality"),
    ("RN3 near Bir Mcherga", 36.5299515, 9.9869744, "national", "DGPC"),
    ("A1 motorway near Bouficha", 36.3382779, 10.4865003, "autoroute", "Ministry of Equipment"),
    ("RR74E near Testour", 36.4468918, 9.3764175, "regional", "DGPC"),
    ("Farm track near Mornag", 36.660000, 10.300000, "piste", "Municipality"),
    ("Gabès centre", 33.881500, 10.098200, "urbain_secondaire", "Municipality"),
]


async def main() -> None:
    headers = {"User-Agent": settings.osm_user_agent}
    cases = []
    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        for name, lat, lon, exp_class, exp_office in POINTS:
            nominatim = (await client.get(f"{settings.nominatim_url}/reverse", params={
                "lat": lat, "lon": lon, "format": "jsonv2", "zoom": 17, "addressdetails": 1, "namedetails": 1,
                "accept-language": "fr"})).json()
            for k in ("licence", "boundingbox", "place_id", "osm_id", "osm_type", "importance", "place_rank"):
                nominatim.pop(k, None)
            got = parse(nominatim, lat, lon)
            kind = office_kind_for(got["road_class"])
            cases.append({"name": name, "lat": lat, "lon": lon, "nominatim": nominatim,
                          "intended": {"road_class": exp_class, "office_kind": exp_office},
                          "expected": {k: got[k] for k in ("road_class", "road_type", "road_ref", "region", "municipality")}})
            ok = "✅" if kind == exp_office else "❌"
            print(f"| {name} | {exp_office} | {got['road_class']} → {kind} {ok} | {got['road_ref'] or ''} | "
                  f"{got['road_name'] or ''} | {got['municipality'] or ''} | {got['region'] or ''} |")
            await asyncio.sleep(1.1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(cases)} fixtures to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())

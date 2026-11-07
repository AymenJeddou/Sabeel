"""OSM enrichment from 20 recorded Nominatim answers (CI never hits the network), road
classification, routing, and the cache (issue #24)."""
import json
from pathlib import Path

import pytest

from backend.app.geo import enrichment
from backend.app.geo.road_class_map import classify, office_kind_for
from backend.app.tests.conftest import db_call

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "osm_points.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIXTURES, ids=[c["name"] for c in FIXTURES])
def test_recorded_points_classify_as_expected(case):
    data = enrichment.parse(case["nominatim"], case["lat"], case["lon"])
    for key, expected in case["expected"].items():
        assert data[key] == expected, f"{case['name']}: {key}"
    assert office_kind_for(data["road_class"]) == case["intended"]["office_kind"], case["name"]


def test_ref_patterns():
    assert classify("primary", "RN1", urban=False) == ("national", "rural")
    assert classify("primary", "RN 9", urban=True) == ("national", "urbain_principal")
    assert classify("secondary", "RR21", urban=False) == ("regional", "rural")
    assert classify("residential", None, urban=True) == ("urbain_secondaire", "urbain_secondaire")
    assert classify("track", None, urban=False) == ("piste", "piste")
    assert classify("motorway", "A1", urban=False) == ("autoroute", "autoroute")
    assert office_kind_for("national") == "DGPC" and office_kind_for("urbain_secondaire") == "Municipality"


def test_routing_national_road_to_dgpc_city_street_to_municipality(client):
    async def route(db, data, lat, lon):
        office = await enrichment.route_office(db, data, lat, lon)
        return office.code

    national = {"road_class": "national", "region": "Ben Arous", "municipality": "Radès"}
    street = {"road_class": "urbain_secondaire", "region": "Tunis", "municipality": "La Marsa"}
    nowhere = {"road_class": "rural", "region": None, "municipality": None}
    assert db_call(client, lambda db: route(db, national, 36.75, 10.25)) == "dre-ben-arous"
    assert db_call(client, lambda db: route(db, street, 36.87, 10.32)) == "mun-la-marsa"
    assert db_call(client, lambda db: route(db, nowhere, 35.83, 10.62)) == "mun-sousse"  # nearest within 20 km


def test_cached_lookup_makes_no_second_call(client, monkeypatch):
    from backend.app.config import settings

    calls = []
    case = FIXTURES[0]

    async def fake_nominatim(_client, lat, lon):
        calls.append("nominatim")
        return case["nominatim"]

    monkeypatch.setattr(settings, "osm_enabled", True)
    monkeypatch.setattr(enrichment, "_nominatim", fake_nominatim)
    first = db_call(client, lambda db: enrichment.lookup(db, case["lat"], case["lon"]))
    second = db_call(client, lambda db: enrichment.lookup(db, case["lat"], case["lon"]))
    assert first == second and calls == ["nominatim"]


def test_osm_down_gives_a_fallback_and_never_fails(client, monkeypatch):
    from backend.app.config import settings

    async def boom(*_):
        return None

    monkeypatch.setattr(settings, "osm_enabled", True)
    monkeypatch.setattr(enrichment, "_nominatim", boom)
    data = db_call(client, lambda db: enrichment.lookup(db, 36.8, 10.18))
    assert data["source"] == "fallback" and data["road_type"] == "urbain_secondaire"  # Tunis city box

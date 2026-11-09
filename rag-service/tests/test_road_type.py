from app.road_type import normalize_road_type, resolve_road_type


def test_city_centres_are_urban_and_the_rest_rural():
    assert resolve_road_type(36.80, 10.18) == "urbain_principal"  # Tunis
    assert resolve_road_type(34.74, 10.76) == "urbain_principal"  # Sfax
    assert resolve_road_type(33.00, 9.00) == "rural"


def test_a_known_road_type_wins_over_the_heuristic():
    assert normalize_road_type("autoroute", 36.80, 10.18) == "autoroute"
    assert normalize_road_type("national", 36.80, 10.18) == "urbain_principal"  # a road_class, not a road_type
    assert normalize_road_type(None, 33.0, 9.0) == "rural"

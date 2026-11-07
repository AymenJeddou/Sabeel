"""Pilot offices: Grand Tunis, Sousse and Sfax.

Each municipality escalates to the regional directorate of equipment of its
governorate (kind DGPC), which escalates to the ministry. Coordinates are the
approximate town-hall / directorate locations, used only to route a pothole
when OpenStreetMap cannot be reached.

(code, name, kind, region, municipality, lat, lon, parent code)
"""

OFFICES: list[tuple[str, str, str, str | None, str | None, float, float, str | None]] = [
    ("ministry", "Ministère de l'Équipement et de l'Habitat", "Ministry of Equipment", None, None, 36.8065, 10.1815, None),
    ("dre-tunis", "Direction Régionale de l'Équipement de Tunis", "DGPC", "Tunis", None, 36.8008, 10.1800, "ministry"),
    ("dre-ariana", "Direction Régionale de l'Équipement de l'Ariana", "DGPC", "Ariana", None, 36.8625, 10.1956, "ministry"),
    ("dre-ben-arous", "Direction Régionale de l'Équipement de Ben Arous", "DGPC", "Ben Arous", None, 36.7531, 10.2189, "ministry"),
    ("dre-manouba", "Direction Régionale de l'Équipement de la Manouba", "DGPC", "Manouba", None, 36.8101, 10.0956, "ministry"),
    ("dre-sousse", "Direction Régionale de l'Équipement de Sousse", "DGPC", "Sousse", None, 35.8256, 10.6360, "ministry"),
    ("dre-sfax", "Direction Régionale de l'Équipement de Sfax", "DGPC", "Sfax", None, 34.7406, 10.7603, "ministry"),
    ("mun-tunis", "Municipalité de Tunis", "Municipality", "Tunis", "Tunis", 36.7992, 10.1706, "dre-tunis"),
    ("mun-le-bardo", "Municipalité du Bardo", "Municipality", "Tunis", "Le Bardo", 36.8092, 10.1406, "dre-tunis"),
    ("mun-la-marsa", "Municipalité de La Marsa", "Municipality", "Tunis", "La Marsa", 36.8782, 10.3247, "dre-tunis"),
    ("mun-la-goulette", "Municipalité de La Goulette", "Municipality", "Tunis", "La Goulette", 36.8183, 10.3050, "dre-tunis"),
    ("mun-carthage", "Municipalité de Carthage", "Municipality", "Tunis", "Carthage", 36.8528, 10.3233, "dre-tunis"),
    ("mun-ariana", "Municipalité de l'Ariana", "Municipality", "Ariana", "Ariana", 36.8665, 10.1647, "dre-ariana"),
    ("mun-ben-arous", "Municipalité de Ben Arous", "Municipality", "Ben Arous", "Ben Arous", 36.7533, 10.2283, "dre-ben-arous"),
    ("mun-rades", "Municipalité de Radès", "Municipality", "Ben Arous", "Radès", 36.7681, 10.2753, "dre-ben-arous"),
    ("mun-manouba", "Municipalité de la Manouba", "Municipality", "Manouba", "Manouba", 36.8081, 10.0972, "dre-manouba"),
    ("mun-sousse", "Municipalité de Sousse", "Municipality", "Sousse", "Sousse", 35.8256, 10.6084, "dre-sousse"),
    ("mun-sfax", "Municipalité de Sfax", "Municipality", "Sfax", "Sfax", 34.7398, 10.7600, "dre-sfax"),
]

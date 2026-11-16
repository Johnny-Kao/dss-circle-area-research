"""Research-only: vary the PlanningArea starting point; keep ZIP v2 fixture logic unchanged."""

import json
from itertools import product
from unittest.mock import patch

import s2sphere

from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    FixtureUnavailable,
    OIRCircleOverlap,
)
from test_oir_circle_v2 import planning_area

AREAS = (
    ("Kentland", 37.2, -80.58),
    ("Stanford", 37.43, -122.17),
    ("Tokyo", 35.68, 139.75),
    ("Zurich", 47.38, 8.54),
    ("Helsinki", 60.17, 24.94),
)
FRACTIONS = (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875)

for name, lat, lng in AREAS:
    resource, volume = planning_area(lat, lng)
    bounds = resource.get_extents()
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = resource
    seen = set()
    for fx, fy in product(FRACTIONS, repeat=2):
        sample = s2sphere.LatLng.from_degrees(
            bounds.lat_min + (bounds.lat_max - bounds.lat_min) * fx,
            bounds.lng_min + (bounds.lng_max - bounds.lng_min) * fy,
        )
        with (
            patch.object(OIRCircleOverlap, "_reference", return_value=sample),
            patch.object(OIRCircleOverlap, "record_note"),
        ):
            try:
                primary, query = scenario._fixture(volume)
            except FixtureUnavailable:
                continue
        key = (
            round(primary.center.lat, 9), round(primary.center.lng, 9),
            round(query.center.lat, 9), round(query.center.lng, 9),
        )
        if key in seen:
            continue
        seen.add(key)
        print(json.dumps({
            "name": name,
            "caseIndex": len(seen)-1,
            "radius": primary.radius.value,
            "primary": [primary.center.lat, primary.center.lng],
            "query": [query.center.lat, query.center.lng],
        }))

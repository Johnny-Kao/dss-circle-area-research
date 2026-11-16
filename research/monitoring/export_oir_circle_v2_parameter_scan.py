"""Research-only: vary v2 constants while preserving its exact fixture algorithm."""

import json
from itertools import product
from unittest.mock import patch

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
RADII = (100.0, 150.0, 200.0, 250.0, 300.0)
DEPTHS = (0.1, 0.25, 0.5)

for name, lat, lng in AREAS:
    planning, area = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = planning
    for radius, depth in product(RADII, DEPTHS):
        index = RADII.index(radius)*len(DEPTHS)+DEPTHS.index(depth)
        with (
            patch.object(OIRCircleOverlap, "OIR_RADIUS_M", radius),
            patch.object(OIRCircleOverlap, "OIR_CROSSING_DEPTH_M", depth),
            patch.object(OIRCircleOverlap, "record_note"),
        ):
            try:
                primary, query = scenario._fixture(area)
            except FixtureUnavailable:
                continue
        print(json.dumps({
            "name": name, "caseIndex": index, "depth": depth,
            "radius": radius,
            "primary": [primary.center.lat, primary.center.lng],
            "query": [query.center.lat, query.center.lng],
        }))

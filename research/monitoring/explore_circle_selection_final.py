"""Research-only broad geometric search. No polygon geometry or vendor code.

Generate valid *true-circle* boundary intersections at several S2 positions.
A separate Go executable observes known old/fixed index sensitivity; the
ASTM-facing generator does not inspect that oracle.
"""
import json
from itertools import product
from math import cos, radians
from unittest.mock import patch

import s2sphere

from monitoring.monitorlib.geo import EARTH_RADIUS_M
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    OIRCircleOverlap,
)
from test_oir_circle_v3 import planning_area

LOCATIONS = (
    ("Kentland", 37.2, -80.58),
    ("Stanford", 37.43, -122.17),
    ("Tokyo", 35.68, 139.75),
    ("Zurich", 47.38, 8.54),
    ("Helsinki", 60.17, 24.94),
) + tuple(
    (f"case-{i:02d}", -62 + ((i * 37 + 13) % 125), -173 + ((i * 59 + 17) % 347))
    for i in range(32)
)

SAMPLES = tuple(i / 6 for i in range(1, 6))
EDGE_FRACTIONS = (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875)
RADII = (100.0, 200.0, 300.0)
CROSSING_M = 0.11
CLEARANCE_M = 0.01

for name, lat, lng in LOCATIONS:
    area, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = area
    bounds = area.get_extents()
    reference = scenario._reference(volume)
    cells = {}
    for fx, fy in product(SAMPLES, repeat=2):
        point = s2sphere.LatLng.from_degrees(
            bounds.lat_min + (bounds.lat_max - bounds.lat_min) * fx,
            bounds.lng_min + (bounds.lng_max - bounds.lng_min) * fy,
        ).to_point()
        cell_id = scenario._cell(point)
        cells[cell_id.id()] = cell_id

    count = 0
    for cell_id in sorted(cells.values(), key=lambda c: c.id()):
        cell = s2sphere.Cell(cell_id)
        neighbors = set(cell_id.get_edge_neighbors())
        for edge in range(4):
            a = cell.get_vertex(edge)
            b = cell.get_vertex((edge + 1) % 4)
            inward = a.cross_prod(b).normalize()
            if inward.dot_prod(cell.get_center()) < 0:
                inward = -inward
            for fraction in EDGE_FRACTIONS:
                boundary = (a * (1 - fraction) + b * fraction).normalize()
                q = scenario._move(
                    boundary, -inward, scenario.QUERY_RADIUS_M + CLEARANCE_M
                )
                qid = scenario._cell(q)
                if qid not in neighbors or not scenario._circle_in_cell(
                    s2sphere.Cell(qid), q, scenario.QUERY_RADIUS_M
                ):
                    continue
                if not scenario._fits(q, scenario.QUERY_RADIUS_M, volume, reference):
                    continue
                for radius in RADII:
                    p = scenario._move(boundary, inward, radius - CROSSING_M)
                    if scenario._cell(p) != cell_id:
                        continue
                    if not scenario._fits(p, radius, volume, reference):
                        continue
                    overlap = (
                        radius + scenario.QUERY_RADIUS_M
                        - p.angle(q) * EARTH_RADIUS_M
                    )
                    if abs(overlap - (CROSSING_M - CLEARANCE_M)) > 0.001:
                        continue
                    oir, query = scenario._circle(p, radius), scenario._circle(q, 1)
                    print(json.dumps({
                        "name": name, "caseIndex": count, "radius": radius,
                        "primary": [oir.center.lat, oir.center.lng],
                        "query": [query.center.lat, query.center.lng],
                        "cell": cell_id.id(), "neighbor": qid.id(),
                        "edge": edge, "fraction": fraction,
                        "overlap": round(overlap, 6),
                    }))
                    count += 1
    print(f"{name}: {count} valid true-circle candidates", file=__import__("sys").stderr)

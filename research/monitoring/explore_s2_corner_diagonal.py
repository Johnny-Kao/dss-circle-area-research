"""Research-only adversarial S2 vertex geometry without historic polygon logic.

For each level-13 cell corner, place a big circular OIR inside that cell and
a 1m circular query wholly inside the *diagonally* neighboring S2 cell.
Their true spherical circles overlap by ~0.1m across the shared vertex.

All failure observations are made independently by Go, never in this
geometry generator. This study does not modify the shipping Scenario.
"""
import json
import sys
from itertools import product

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

SAMPLES = tuple(i / 8 for i in range(1, 8))
RADII_M = (200.0, 300.0)
QUERY_CORNER_DISTANCES_M = (1.7, 2.5, 4.0)
OVERLAP_M = 0.1
MAX_PER_AREA = 400

for name, lat, lng in LOCATIONS:
    resource, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = resource
    reference = scenario._reference(volume)
    bounds = resource.get_extents()
    cells = {}
    for fx, fy in product(SAMPLES, repeat=2):
        sample = s2sphere.LatLng.from_degrees(
            bounds.lat_min + (bounds.lat_max - bounds.lat_min) * fx,
            bounds.lng_min + (bounds.lng_max - bounds.lng_min) * fy,
        ).to_point()
        cell = scenario._cell(sample)
        cells[cell.id()] = cell

    seen = set()
    count = 0
    for source in sorted(cells.values(), key=lambda c: c.id()):
        cell = s2sphere.Cell(source)
        center = cell.get_center()
        neighbors = set(source.get_edge_neighbors())
        for vertex_number in range(4):
            vertex = cell.get_vertex(vertex_number)
            tangent = (center - vertex * center.dot_prod(vertex)).normalize()
            for qdistance in QUERY_CORNER_DISTANCES_M:
                q = scenario._move(vertex, -tangent, qdistance)
                qid = scenario._cell(q)
                if qid == source or qid in neighbors:
                    continue
                if not scenario._circle_in_cell(s2sphere.Cell(qid), q, 1.0):
                    continue
                if not scenario._fits(q, 1.0, volume, reference):
                    continue
                for radius in RADII_M:
                    p = scenario._move(
                        vertex, tangent, radius - (qdistance - 1.0 + OVERLAP_M)
                    )
                    if scenario._cell(p) != source:
                        continue
                    if not scenario._fits(p, radius, volume, reference):
                        continue
                    overlap = radius + 1.0 - p.angle(q) * EARTH_RADIUS_M
                    if not (0.098 < overlap < 0.102):
                        continue
                    primary, query = scenario._circle(p, radius), scenario._circle(q, 1.0)
                    unique = (
                        source.id(), qid.id(), vertex_number, qdistance, radius
                    )
                    if unique in seen:
                        continue
                    seen.add(unique)
                    print(json.dumps({
                        "name": name,
                        "caseIndex": count,
                        "radius": radius,
                        "primary": [primary.center.lat, primary.center.lng],
                        "query": [query.center.lat, query.center.lng],
                        "sourceCell": source.id(),
                        "queryCell": qid.id(),
                        "vertex": vertex_number,
                        "cornerDistanceM": qdistance,
                        "overlapM": round(overlap, 6),
                    }))
                    count += 1
                    if count >= MAX_PER_AREA:
                        break
                if count >= MAX_PER_AREA:
                    break
            if count >= MAX_PER_AREA:
                break
        if count >= MAX_PER_AREA:
            break
    print(f"{name}: {count} valid diagonal-corner circles", file=sys.stderr)

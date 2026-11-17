"""Research-only independent true-circle depth/clearance scan.

Tests whether the search query's covering near an S2 edge is preventing old
false negatives. Neither the fixture generator nor proposed ASTM Scenario
uses historical polygon geometry. Historical index is inspected *afterward*.
"""
import json
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
# All maintain an exact ~0.10 m overlap; only the distance of the *entire*
# query from the S2 boundary changes.
DEPTHS = ((.11, .01), (.25, .15), (.5, .4), (1., .9), (2., 1.9))
RADII = (100., 200., 300.)
FRACTIONS = (.25, .5, .75)
SAMPLES = (.25, .5, .75)

for name, lat, lng in LOCATIONS:
    resource, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = resource
    reference = scenario._reference(volume)
    bounds = resource.get_extents()
    cells = {}
    for fx, fy in product(SAMPLES, repeat=2):
        p = s2sphere.LatLng.from_degrees(
            bounds.lat_min + (bounds.lat_max - bounds.lat_min) * fx,
            bounds.lng_min + (bounds.lng_max - bounds.lng_min) * fy,
        ).to_point()
        cid = scenario._cell(p)
        cells[cid.id()] = cid

    case_index = 0
    for cid in sorted(cells.values(), key=lambda c: c.id()):
        cell = s2sphere.Cell(cid)
        neighbors = set(cid.get_edge_neighbors())
        for edge in range(4):
            a, b = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
            inward = a.cross_prod(b).normalize()
            if inward.dot_prod(cell.get_center()) < 0:
                inward = -inward
            for fraction in FRACTIONS:
                boundary = (a * (1-fraction) + b*fraction).normalize()
                for depth, clearance in DEPTHS:
                    q = scenario._move(boundary, -inward, 1. + clearance)
                    qid = scenario._cell(q)
                    if qid not in neighbors or not scenario._circle_in_cell(
                        s2sphere.Cell(qid), q, 1.
                    ) or not scenario._fits(q, 1., volume, reference):
                        continue
                    for radius in RADII:
                        p = scenario._move(boundary, inward, radius - depth)
                        if scenario._cell(p) != cid or not scenario._fits(
                            p, radius, volume, reference
                        ):
                            continue
                        overlap = radius + 1. - p.angle(q) * EARTH_RADIUS_M
                        if not (0.099 < overlap < 0.101):
                            continue
                        oir, query = scenario._circle(p, radius), scenario._circle(q, 1.)
                        print(json.dumps({
                            "name": name, "caseIndex": case_index,
                            "radius": radius,
                            "primary": [oir.center.lat, oir.center.lng],
                            "query": [query.center.lat, query.center.lng],
                            "edge": edge,
                            "fraction": fraction,
                            "depth": depth,
                            "clearance": clearance,
                            "overlap": overlap,
                        }))
                        case_index += 1
    print(f"{name}: {case_index} valid slivers", file=__import__("sys").stderr)

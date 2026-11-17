"""Research-only *tilted* circle-overlap search at true S2 diagonal vertices.

A 1m query circle lies entirely inside a diagonal S2 cell. The larger
registered circle is placed in the source cell at exactly R+0.9m from
query center, rotating the centerline in the source cell without
any polygon or vendor-specific selection criteria.
"""
import json
import sys
from itertools import product
from math import cos, radians, sin

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
RADII_M = (100.0, 200.0, 300.0)
QUERY_CORNER_DISTANCES_M = (1.7, 2.5)
TILTS_DEG = (-36, -30, -24, -18, -12, -6, 0, 6, 12, 18, 24, 30, 36)
OVERLAP_M = 0.1
MAX_PER_AREA = 600

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
        cellid = scenario._cell(sample)
        cells[cellid.id()] = cellid

    seen = set()
    count = 0
    for source in sorted(cells.values(), key=lambda c: c.id()):
        cell = s2sphere.Cell(source)
        center = cell.get_center()
        neighbors = set(source.get_edge_neighbors())
        for vertex_number in range(4):
            vertex = cell.get_vertex(vertex_number)
            inward = (center - vertex * center.dot_prod(vertex)).normalize()
            for qdistance in QUERY_CORNER_DISTANCES_M:
                q = scenario._move(vertex, -inward, qdistance)
                qid = scenario._cell(q)
                if qid == source or qid in neighbors:
                    continue
                if not scenario._circle_in_cell(s2sphere.Cell(qid), q, 1.0):
                    continue
                if not scenario._fits(q, 1.0, volume, reference):
                    continue
                to_vertex = (vertex - q * q.dot_prod(vertex)).normalize()
                sideways = q.cross_prod(to_vertex).normalize()
                for tilt_deg in TILTS_DEG:
                    angle = radians(tilt_deg)
                    direction = (to_vertex * cos(angle) + sideways * sin(angle)).normalize()
                    for radius in RADII_M:
                        p = scenario._move(q, direction, radius + 1.0 - OVERLAP_M)
                        if scenario._cell(p) != source:
                            continue
                        if not scenario._fits(p, radius, volume, reference):
                            continue
                        overlap = radius + 1.0 - p.angle(q) * EARTH_RADIUS_M
                        if not (0.098 < overlap < 0.102):
                            continue
                        primary, query = scenario._circle(p, radius), scenario._circle(q, 1.0)
                        unique = (source.id(), qid.id(), vertex_number, qdistance, tilt_deg, radius)
                        if unique in seen:
                            continue
                        seen.add(unique)
                        print(json.dumps({
                            "name": name, "caseIndex": count, "radius": radius,
                            "primary": [primary.center.lat, primary.center.lng],
                            "query": [query.center.lat, query.center.lng],
                            "sourceCell": source.id(), "queryCell": qid.id(),
                            "vertex": vertex_number, "cornerDistanceM": qdistance,
                            "tiltDeg": tilt_deg, "overlapM": round(overlap, 6),
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
        if count >= MAX_PER_AREA:
            break
    print(f"{name}: {count} valid tilted-corner circles", file=sys.stderr)

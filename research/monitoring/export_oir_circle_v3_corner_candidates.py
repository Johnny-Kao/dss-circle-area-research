"""Research-only exploration of genuine S2 corner-crossing circular OIR queries.

The candidate generation does NOT use the historical polygon implementation.
The independent Go S2 oracle is used afterwards, strictly to measure how often
these valid geometry fixtures detect the known old DSS defect.
"""

import json
from itertools import product

import s2sphere

from monitoring.monitorlib.geo import EARTH_RADIUS_M
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import OIRCircleOverlap
from test_oir_circle_v2 import planning_area

AREAS = (
    ("Kentland", 37.2, -80.58),
    ("Stanford", 37.43, -122.17),
    ("Tokyo", 35.68, 139.75),
    ("Zurich", 47.38, 8.54),
    ("Helsinki", 60.17, 24.94),
)
SAMPLES = (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875)
RADII = (150.0, 200.0, 250.0, 300.0)
OFFSETS = ((1.1, 1.7), (1.5, 2.0), (2.0, 2.5))  # (true circle crossing, query center beyond corner)
LIMIT_PER_REGION = 640

for name, lat, lng in AREAS:
    area_resource, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = area_resource
    reference = scenario._reference(volume)
    bounds = area_resource.get_extents()
    cells = {}
    for fx, fy in product(SAMPLES, repeat=2):
        point = s2sphere.LatLng.from_degrees(
            bounds.lat_min + (bounds.lat_max-bounds.lat_min)*fx,
            bounds.lng_min + (bounds.lng_max-bounds.lng_min)*fy,
        ).to_point()
        cid = scenario._cell(point)
        cells[cid.id()] = cid
    emitted = 0
    for cid in sorted(cells.values(), key=lambda x:x.id()):
        cell = s2sphere.Cell(cid)
        vertex_ids = []
        for i in range(4):
            vertex = cell.get_vertex(i)
            # At the vertex, the unit tangent pointing toward the source cell.
            center = cell.get_center()
            toward = (center-vertex*center.dot_prod(vertex)).normalize()
            out = -toward
            for radius in RADII:
                for depth, query_offset in OFFSETS:
                    primary_center = scenario._move(vertex, toward, radius-depth)
                    query_center = scenario._move(vertex, out, query_offset)
                    if scenario._cell(primary_center) != cid:
                        continue
                    query_id = scenario._cell(query_center)
                    if query_id == cid or query_id in cid.get_edge_neighbors():
                        continue
                    if not scenario._circle_in_cell(
                        s2sphere.Cell(query_id),query_center,scenario.QUERY_RADIUS_M
                    ):
                        continue
                    if not scenario._fits(primary_center,radius,volume,reference):
                        continue
                    if not scenario._fits(query_center,scenario.QUERY_RADIUS_M,volume,reference):
                        continue
                    overlap = radius+scenario.QUERY_RADIUS_M-primary_center.angle(query_center)*EARTH_RADIUS_M
                    if not 0.05 < overlap < 1.0:
                        continue
                    primary = scenario._circle(primary_center,radius)
                    query = scenario._circle(query_center,scenario.QUERY_RADIUS_M)
                    print(json.dumps({
                        "name":name,"caseIndex":emitted,
                        "radius":radius,
                        "primary":[primary.center.lat,primary.center.lng],
                        "query":[query.center.lat,query.center.lng],
                        "sourceCell":cid.id(),"queryCell":query_id.id(),
                        "vertex":i,"depth":depth,"queryOffset":query_offset,
                        "trueOverlap":overlap,
                    }))
                    emitted+=1
                    if emitted >= LIMIT_PER_REGION:
                        break
                if emitted >= LIMIT_PER_REGION:
                    break
            if emitted >= LIMIT_PER_REGION:
                break
        if emitted >= LIMIT_PER_REGION:
            break
    print(f"{name}: valid corner candidates={emitted}",file=__import__('sys').stderr)

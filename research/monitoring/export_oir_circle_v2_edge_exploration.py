"""Research-only: enumerate genuine circular overlaps at different S2 edges.

No historical covering oracle in the permanent ASTM Scenario.  A separate Go
research oracle tests each constructed pair against old/fixed DSS S2 coverings.
"""

import json
from unittest.mock import patch

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

for name, lat, lng in AREAS:
    resource, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = resource
    with patch.object(OIRCircleOverlap, "record_note"):
        selected_primary, selected_query = scenario._fixture(volume)
    reference_ll = scenario._reference(volume)
    reference = reference_ll.to_point()
    source_id = scenario._cell(reference)
    cell = s2sphere.Cell(source_id)
    neighbors = set(source_id.get_edge_neighbors())
    cases = []

    for edge in range(4):
        midpoint, inward = scenario._edge(cell, edge)
        for fraction in (0.25, 0.5, 0.75):
            a, b = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
            boundary = (a * (1 - fraction) + b * fraction).normalize()
            primary_center = scenario._move(
                boundary, inward, scenario.OIR_RADIUS_M - scenario.OIR_CROSSING_DEPTH_M
            )
            query_center = scenario._move(
                boundary, -inward, scenario.QUERY_RADIUS_M + scenario.QUERY_BOUNDARY_CLEARANCE_M
            )
            if scenario._cell(primary_center) != source_id:
                continue
            query_id = scenario._cell(query_center)
            if query_id not in neighbors:
                continue
            if not scenario._circle_in_cell(
                s2sphere.Cell(query_id), query_center, scenario.QUERY_RADIUS_M
            ):
                continue
            if not scenario._fits(primary_center, scenario.OIR_RADIUS_M, volume, reference_ll):
                continue
            if not scenario._fits(query_center, scenario.QUERY_RADIUS_M, volume, reference_ll):
                continue
            overlap = scenario.OIR_RADIUS_M + scenario.QUERY_RADIUS_M - primary_center.angle(query_center)*EARTH_RADIUS_M
            if overlap <= 0:
                continue
            p = scenario._circle(primary_center, scenario.OIR_RADIUS_M)
            q = scenario._circle(query_center, scenario.QUERY_RADIUS_M)
            selected = abs(p.center.lat-selected_primary.center.lat)<1e-7 and abs(p.center.lng-selected_primary.center.lng)<1e-7
            cases.append((edge, fraction, p, q, selected))
    for index, (edge, fraction, primary, query, selected) in enumerate(cases):
        print(json.dumps({
            "name": name, "caseIndex": index, "edge": edge, "fraction": fraction,
            "selected": selected, "radius": primary.radius.value,
            "primary": [primary.center.lat, primary.center.lng],
            "query": [query.center.lat, query.center.lng],
        }))

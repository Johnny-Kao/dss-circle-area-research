"""Research-only independent 37-region confirmation of the exact Scenario fixtures.

The production Scenario never imports historical S2 polygons. This exporter
validates true-circle overlap and the query being wholly in a diagonal Cell;
a separate Go index oracle checks historical error sensitivity.
"""
import json
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

for name, lat, lng in LOCATIONS:
    resource, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = resource
    with patch.object(OIRCircleOverlap, "record_note") as notes:
        fixtures = scenario._fixtures(volume)
    assert len(fixtures) == 4, (name, len(fixtures))
    assert len(notes.call_args_list) == 4
    corners = {
        (
            int(call.args[1].split("source_cell=")[1].split(";")[0]),
            int(call.args[1].split("corner=")[1].split(";")[0]),
        )
        for call in notes.call_args_list
    }
    assert len(corners) == 4, (name, corners)
    reference = scenario._reference(volume)
    for index, (primary, query) in enumerate(fixtures):
        p = primary.center.as_s2sphere().to_point()
        q = query.center.as_s2sphere().to_point()
        r = primary.radius.value
        qr = query.radius.value
        overlap = r + qr - p.angle(q) * EARTH_RADIUS_M
        assert r == 300 and qr == 1, (name, index, r, qr)
        assert 0.098 < overlap < 0.102, (name, index, overlap)
        source, dest = scenario._cell(p), scenario._cell(q)
        assert source != dest and dest not in source.get_edge_neighbors(), (
            name, index, source, dest
        )
        assert scenario._circle_in_cell(s2sphere.Cell(dest), q, qr), (name, index)
        assert scenario._fits(p, r, volume, reference), (name, index)
        assert scenario._fits(q, qr, volume, reference), (name, index)
        print(json.dumps({
            "name": name, "caseIndex": index,
            "radius": r,
            "primary": [primary.center.lat, primary.center.lng],
            "query": [query.center.lat, query.center.lng],
        }))

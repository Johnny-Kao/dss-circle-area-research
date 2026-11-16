"""Research-only generalization study of the production-facing four-axis fixture.

The geometry oracle is independent: deliberately no historical InterUSS
polygon or vendor-code checks in this generator. This is not a proof of every
possible planning area; it checks a diverse, predetermined set of locations.
"""
import json
from unittest.mock import patch

import s2sphere

from monitoring.monitorlib.geo import EARTH_RADIUS_M
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    OIRCircleOverlap,
)
from test_oir_circle_v3 import planning_area

# Deterministic broad geographic spread, independent of previous test locations.
LOCATIONS = tuple(
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
    edges = {
        int(call.args[1].split("edge=")[1].split(";")[0])
        for call in notes.call_args_list
    }
    assert edges == {0, 1, 2, 3}, (name, edges)
    reference = scenario._reference(volume)
    for index, (primary, query) in enumerate(fixtures):
        p, q = primary.center.as_s2sphere().to_point(), query.center.as_s2sphere().to_point()
        overlap = (
            primary.radius.value
            + query.radius.value
            - p.angle(q) * EARTH_RADIUS_M
        )
        assert 0.08 < overlap < 0.12, (name, index, overlap)
        p_id, q_id = scenario._cell(p), scenario._cell(q)
        assert p_id != q_id and q_id in p_id.get_edge_neighbors(), (name, index)
        assert scenario._circle_in_cell(
            s2sphere.Cell(q_id), q, query.radius.value
        ), (name, index)
        assert scenario._fits(p, primary.radius.value, volume, reference), (name, index)
        assert scenario._fits(q, query.radius.value, volume, reference), (name, index)
        print(json.dumps({
            "name": name, "caseIndex": index,
            "radius": primary.radius.value,
            "primary": [primary.center.lat, primary.center.lng],
            "query": [query.center.lat, query.center.lng],
        }))

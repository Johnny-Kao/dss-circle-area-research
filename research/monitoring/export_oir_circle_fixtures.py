"""Export actual submitted scenario fixtures to the independent Go S2 oracle.

Unlike the existing candidate generator, this checks exact circles selected
by OIRCircleOverlap._fixtures(), including the order and fixture cap.
"""

import json
from unittest.mock import patch

from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    OIRCircleOverlap,
)
from test_oir_circle_contract import planning_area

AREAS = (
    ("Kentland", 37.2, -80.58),
    ("Stanford", 37.43, -122.17),
    ("Tokyo", 35.68, 139.75),
    ("Zurich", 47.38, 8.54),
    ("Helsinki", 60.17, 24.94),
)

for name, lat, lng in AREAS:
    planning, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = planning
    with patch.object(OIRCircleOverlap, "record_note"):
        fixtures = scenario._fixtures(volume)
    for index, (primary, query) in enumerate(fixtures):
        print(
            json.dumps(
                {
                    "name": name,
                    "caseIndex": index,
                    "radius": primary.radius.value,
                    "primary": [primary.center.lat, primary.center.lng],
                    "query": [query.center.lat, query.center.lng],
                }
            )
        )

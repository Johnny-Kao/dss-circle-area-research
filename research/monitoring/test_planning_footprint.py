"""Unit regressions for actual PlanningAreaResource footprint containment."""
import unittest

import s2sphere

from monitoring.monitorlib.geo import Circle, LatLngPoint, Polygon, Volume3D
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    OIRCircleOverlap,
)


def pt(lat, lng):
    return s2sphere.LatLng.from_degrees(lat, lng).to_point()


class PlanningFootprintTest(unittest.TestCase):
    def setUp(self):
        self.reference = s2sphere.LatLng.from_degrees(35.68, 139.75)
        self.l_shape = Volume3D(
            outline_polygon=Polygon(
                vertices=[
                    LatLngPoint(lat=35.67, lng=139.74),
                    LatLngPoint(lat=35.67, lng=139.76),
                    LatLngPoint(lat=35.68, lng=139.76),
                    LatLngPoint(lat=35.68, lng=139.75),
                    LatLngPoint(lat=35.69, lng=139.75),
                    LatLngPoint(lat=35.69, lng=139.74),
                ]
            )
        )

    def inside(self, lat, lng, radius, volume=None):
        return OIRCircleOverlap._circle_inside_volume(
            pt(lat, lng),
            radius,
            self.l_shape if volume is None else volume,
            self.reference,
        )

    def test_concave_cutout_is_not_planning_area(self):
        # In the bounding rectangle, but outside the six-vertex L footprint.
        self.assertFalse(self.inside(35.685, 139.755, 1))

    def test_entire_circle_inside_concave_footprint(self):
        self.assertTrue(self.inside(35.675, 139.745, 50))

    def test_circle_protruding_past_polygon_edge_rejected(self):
        # Center lies in the L footprint; 50 m radius extends past east edge.
        self.assertFalse(self.inside(35.675, 139.7598, 50))

    def test_circle_planning_area(self):
        area = Volume3D(outline_circle=Circle.from_meters(35.68, 139.75, 400))
        self.assertTrue(self.inside(35.68, 139.75, 50, area))
        self.assertFalse(self.inside(35.683, 139.75, 100, area))


if __name__ == "__main__":
    unittest.main()

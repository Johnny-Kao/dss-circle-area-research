"""Independent ASTM search-contract checks for the PR #1911 Research candidate.

These checks are deliberately separate from the production-facing scenario.
They do not require the historical InterUSS 20-gon implementation.
"""

from datetime import UTC, datetime, timedelta
from math import cos, radians
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

import s2sphere

from monitoring.monitorlib.geo import (
    Circle,
    LatLngBoundingBox,
    LatLngPoint,
    Polygon,
    Volume3D,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    FixtureUnavailable,
    OIRCircleOverlap,
)


def planning_area(lat, lng, width_m=6000, height_m=3300):
    """An area-relative rectangle; no original bug coordinate is required."""
    lat_half = height_m / 2 / 111195
    lng_half = width_m / 2 / (111195 * cos(radians(lat)))
    south, north = lat - lat_half, lat + lat_half
    west, east = lng - lng_half, lng + lng_half
    volume = Volume3D(
        outline_polygon=Polygon(
            vertices=[
                LatLngPoint(lat=south, lng=west),
                LatLngPoint(lat=south, lng=east),
                LatLngPoint(lat=north, lng=east),
                LatLngPoint(lat=north, lng=west),
            ]
        )
    )
    bounds = LatLngBoundingBox(
        lat_min=south, lat_max=north, lng_min=west, lng_max=east
    )
    resource = SimpleNamespace(get_extents=lambda: bounds)
    return resource, volume


class CircularOverlapContractTests(TestCase):
    def test_actual_geometry_is_positive_and_crosses_cell_boundary(self):
        areas = (
            ("Kentland", 37.2, -80.58),
            ("Stanford", 37.43, -122.17),
            ("Tokyo", 35.68, 139.75),
            ("Zurich", 47.38, 8.54),
            ("Helsinki", 60.17, 24.94),
        )
        for place, lat, lng in areas:
            with self.subTest(place=place):
                resource, volume = planning_area(lat, lng)
                scenario = object.__new__(OIRCircleOverlap)
                scenario._planning_area = resource
                with patch.object(OIRCircleOverlap, "record_note"):
                    fixtures = scenario._fixtures(volume)
                self.assertGreaterEqual(len(fixtures), 1)
                self.assertLessEqual(len(fixtures), scenario.MAX_FIXTURES)
                center = s2sphere.LatLng.from_degrees(lat, lng)
                for primary, query in fixtures:
                    p = primary.center.as_s2sphere().to_point()
                    q = query.center.as_s2sphere().to_point()
                    r = primary.radius.in_meters()
                    qr = query.radius.in_meters()
                    overlap = r + qr - p.angle(q) * scenario.EARTH_RADIUS_M
                    self.assertGreater(overlap, 0, "An actually intersecting OIR is required")
                    self.assertLess(overlap, 1, "Only a narrow near-boundary overlap is expected")
                    self.assertEqual(qr, 1)
                    self.assertNotEqual(scenario._cell(p), scenario._cell(q))
                    self.assertTrue(
                        scenario._circle_in_cell(
                            s2sphere.Cell(scenario._cell(q)), q, qr
                        )
                    )
                    self.assertTrue(scenario._fits(p, r, volume, center))
                    self.assertTrue(scenario._fits(q, qr, volume, center))

    def test_too_small_area_cannot_silently_pass(self):
        resource, volume = planning_area(37.2, -80.58, width_m=50, height_m=50)
        scenario = object.__new__(OIRCircleOverlap)
        scenario._planning_area = resource
        with self.assertRaises(FixtureUnavailable):
            scenario._fixtures(volume)

    def test_extra_nonintersecting_results_are_permitted(self):
        """ASTM search has a positive completeness requirement, not exact membership."""
        scenario = object.__new__(OIRCircleOverlap)
        scenario._oir_id = "registered-oir"
        scenario._participants = ["dss"]
        response = SimpleNamespace(request=SimpleNamespace(timestamp=datetime.now(UTC)))
        scenario._dss = SimpleNamespace(
            find_op_intent=lambda _query: (
                [SimpleNamespace(id="registered-oir"), SimpleNamespace(id="additional")],
                response,
            )
        )
        with (
            patch.object(OIRCircleOverlap, "check") as check_factory,
            patch.object(OIRCircleOverlap, "record_query"),
        ):
            scenario._check_found(
                "Boundary overlap is discoverable",
                Circle.from_meters(37.2, -80.58, 1),
                datetime.now(UTC),
                datetime.now(UTC) + timedelta(minutes=60),
                30,
                120,
            )
            check_factory.return_value.__enter__.return_value.record_failed.assert_not_called()

    def test_missing_overlapping_oir_is_a_real_failed_check(self):
        """Fault injection must be detected; an HTTP success is not enough."""
        scenario = object.__new__(OIRCircleOverlap)
        scenario._oir_id = "registered-oir"
        scenario._participants = ["dss"]
        response = SimpleNamespace(request=SimpleNamespace(timestamp=datetime.now(UTC)))
        scenario._dss = SimpleNamespace(
            find_op_intent=lambda _query: ([SimpleNamespace(id="unrelated")], response)
        )
        with (
            patch.object(OIRCircleOverlap, "check") as check_factory,
            patch.object(OIRCircleOverlap, "record_query"),
        ):
            scenario._check_found(
                "Boundary overlap is discoverable",
                Circle.from_meters(37.2, -80.58, 1),
                datetime.now(UTC),
                datetime.now(UTC) + timedelta(minutes=60),
                30,
                120,
            )
            check_factory.return_value.__enter__.return_value.record_failed.assert_called_once()
            failure = check_factory.return_value.__enter__.return_value.record_failed.call_args
            self.assertEqual(failure.kwargs["summary"], "Overlapping OIR was missing")

    def test_scenario_documentation_matches_review_contract(self):
        docs = Path(__file__).with_name("oir_circle_overlap_standalone.md").read_text()
        self.assertIn("one at a time", docs)
        self.assertIn("additional search results are permitted", docs)
        self.assertIn("#### ⚠️ Boundary overlap is discoverable check", docs)
        self.assertIn("#### 🛑 Ordinary contained circle discovers OIR check", docs)
        self.assertIn("Client to a DSS instance with", docs)
        self.assertIn("DSS0005,2", docs)
        self.assertNotIn("must not return", docs.lower())
        self.assertNotIn("interuss/dss#", docs.lower())
        self.assertNotIn("Kentland", docs)


if __name__ == "__main__":
    main()

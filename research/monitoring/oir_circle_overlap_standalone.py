"""DSS circular OIR search: boundary and ordinary positive-overlap checks."""

from datetime import UTC, datetime, timedelta
from math import asin, atan2, cos, degrees, radians, sin

import s2sphere
from shapely.geometry import Point, Polygon
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    PutOperationalIntentReferenceParameters,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geo import Circle, flatten
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.ids import register_resource_type
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.oir import (
    crud as oir_fragments,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class FixtureUnavailable(Exception):
    """Configured Planning Area cannot hold a valid search fixture."""


class OIRCircleOverlap(TestScenario):
    """Verify that genuine circular OIR overlaps are discoverable."""

    OIR_TYPE = register_resource_type(407, "Circular overlap operational intent")
    EARTH_RADIUS_M = 6371010.0
    # Relative positions, not fixed GPS coordinates or DSS implementation rules.
    PATTERNS = (
        (0.00375, -0.01050, 1100, 0.998),
        (0.00625, 0.00700, 700, 0.998),
        (0.00375, 0.00000, 700, 0.998),
        (0.00125, -0.02100, 900, 0.995),
    )
    BEARINGS = (15, 81, 84, 87)

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
    ):
        super().__init__()
        self._dss = dss.get_instance(
            {Scope.StrategicCoordination: "create and query OIRs"}
        )
        self._participants = [self._dss.participant_id]
        self._oir_id = id_generator.id_factory.make_id(self.OIR_TYPE)
        self._planning_area = planning_area
        self._created_oir = None

    @classmethod
    def _point_at(cls, lat, lng, meters, bearing):
        """Destination on the sphere, at a distance and initial bearing."""
        a, b, d, direction = (
            radians(lat),
            radians(lng),
            meters / cls.EARTH_RADIUS_M,
            radians(bearing),
        )
        lat2 = asin(sin(a) * cos(d) + cos(a) * sin(d) * cos(direction))
        lng2 = b + atan2(
            sin(direction) * sin(d) * cos(a),
            cos(d) - sin(a) * sin(lat2),
        )
        return degrees(lat2), degrees(lng2)

    @classmethod
    def _fits(cls, circle, area, reference):
        """Keep the entire test circle within the actual configured footprint."""
        center = circle.center.as_s2sphere().to_point()
        radius = circle.radius.in_meters()
        if area.outline_circle is not None:
            outer = area.outline_circle
            midpoint = outer.center.as_s2sphere().to_point()
            return (
                center.angle(midpoint) * cls.EARTH_RADIUS_M + radius + 1
                < outer.radius.in_meters()
            )
        if area.outline_polygon is None:
            raise FixtureUnavailable("Planning Area has no circle or polygon")
        polygon = Polygon(
            flatten(reference, p.as_s2sphere()) for p in area.outline_polygon.vertices
        )
        if not polygon.is_valid or polygon.is_empty:
            raise FixtureUnavailable("Planning Area polygon is not valid")
        return polygon.buffer(-(radius + 1)).covers(
            Point(*flatten(reference, circle.center.as_s2sphere()))
        )

    @staticmethod
    def _altitudes(area):
        low = area.altitude_lower_wgs84_m() if area.altitude_lower else None
        high = area.altitude_upper_wgs84_m() if area.altitude_upper else None
        if low is None and high is None:
            low, high = 30.0, 120.0
        elif low is None:
            low = high - 90.0
        elif high is None:
            high = low + 90.0
        if low >= high:
            raise FixtureUnavailable("Planning Area has no positive altitude span")
        return low + (high - low) / 4, high - (high - low) / 4

    def _fixtures(self, area):
        bounds = self._planning_area.get_extents()
        mid_lat = (bounds.lat_min + bounds.lat_max) / 2
        mid_lng = (bounds.lng_min + bounds.lng_max) / 2
        reference = s2sphere.LatLng.from_degrees(mid_lat, mid_lng)
        fixtures = []
        for index, (dlat, dlng, radius, fraction) in enumerate(self.PATTERNS):
            lat, lng = mid_lat + dlat, mid_lng + dlng
            primary = Circle.from_meters(lat, lng, radius)
            probes = [
                Circle.from_meters(
                    *self._point_at(lat, lng, radius * fraction, bearing), 1.0
                )
                for bearing in self.BEARINGS
            ]
            if not all(
                self._fits(circle, area, reference) for circle in (primary, *probes)
            ):
                continue
            fixtures.append((primary, probes))
            self.record_note("fixture_constructed", f"pattern={index}; radius_m={radius}")
        if not fixtures:
            raise FixtureUnavailable(f"No valid circle fixture fits {bounds}")
        return fixtures

    def _check_found(self, name, circle, start, end, alt0, alt1):
        query = Volume4D.from_values(
            t0=start, t1=end, alt0=alt0, alt1=alt1, circle=circle
        ).to_f3548v21()
        with self.check(name, self._participants) as check:
            try:
                found, response = self._dss.find_op_intent(query)
                self.record_query(response)
                if self._oir_id not in {oir.id for oir in found}:
                    check.record_failed(
                        summary="Overlapping OIR was missing",
                        details=f"OIR id={self._oir_id}; query={circle}",
                        query_timestamps=[response.request.timestamp],
                    )
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="Search failed",
                    details=f"HTTP {e.cause_status_code}: {e.msg}",
                    query_timestamps=e.query_timestamps,
                )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        area = self._planning_area.resolved_volume4d_with_times(None, None).volume
        alt0, alt1 = self._altitudes(area)
        fixtures = self._fixtures(area)

        self.begin_test_case("Setup")
        self.begin_test_step("Clear previous test OIR")
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Overlapping circular OIR is discoverable")
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=60)
        for primary, probes in fixtures:
            self.begin_test_step("Create circular OIR")
            params = PutOperationalIntentReferenceParameters(
                extents=[
                    Volume4D.from_values(
                        t0=start, t1=end, alt0=alt0, alt1=alt1, circle=primary
                    ).to_f3548v21()
                ],
                key=[],
                state=OperationalIntentState.Accepted,
                uss_base_url=make_fake_url(),
                subscription_id=None,
            )
            self._created_oir, _, _ = oir_fragments.create_oir_query(
                scenario=self, dss=self._dss, oir_id=self._oir_id, oir_params=params
            )
            self.end_test_step()

            self.begin_test_step("Discover boundary-overlapping OIR")
            for query_circle in probes:
                self._check_found(
                    "Boundary overlap is discoverable",
                    query_circle, start, end, alt0, alt1,
                )
            self.end_test_step()

            self.begin_test_step("Ordinary contained circle discovers OIR")
            inside = Circle.from_meters(
                primary.center.lat, primary.center.lng, 200.0
            )
            self._check_found(
                "Ordinary contained circle discovers OIR",
                inside, start, end, alt0, alt1,
            )
            self.end_test_step()

            self.begin_test_step("Delete circular OIR")
            oir_fragments.delete_oir_query(
                scenario=self,
                dss=self._dss,
                oir_id=self._oir_id,
                ovn=self._created_oir.ovn,
            )
            self._created_oir = None
            self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_cleanup()

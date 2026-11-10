"""API regression for circular OIR overlap at the S2 covering boundary."""

from datetime import UTC, datetime, timedelta
from math import asin, atan2, cos, degrees, radians, sin

from uas_standards.astm.f3548.v21.api import (
    OperationalIntentState,
    PutOperationalIntentReferenceParameters,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.fetch import QueryError
from monitoring.monitorlib.geo import Circle
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.ids import register_resource_type
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.oir import (
    crud as oir_fragments,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class OIRCircleOverlap(TestScenario):
    """Check that a small circle overlapping the edge of a larger OIR is searchable."""

    OIR_TYPE = register_resource_type(
        407, "Circle overlap operational intent reference"
    )

    _RADIUS_M = 1100
    _EARTH_RADIUS_M = 6371008.8

    @staticmethod
    def _point_at(lat: float, lng: float, meters: float, bearing: float):
        """A point at a given bearing on a spherical Earth."""
        lat1, lng1, angle = (
            radians(lat),
            radians(lng),
            meters / OIRCircleOverlap._EARTH_RADIUS_M,
        )
        direction = radians(bearing)
        lat2 = asin(sin(lat1) * cos(angle) + cos(lat1) * sin(angle) * cos(direction))
        lng2 = lng1 + atan2(
            sin(direction) * sin(angle) * cos(lat1),
            cos(angle) - sin(lat1) * sin(lat2),
        )
        return degrees(lat2), degrees(lng2)

    def _circles(self):
        bounds = self._planning_area.get_extents()
        # Keep the original Kentland fixture offset from the area center.
        lat = (bounds.lat_min + bounds.lat_max) / 2 + 0.00095
        lng = (bounds.lng_min + bounds.lng_max) / 2 + 0.003
        # Fail explicitly when a configured area cannot fit the test geometry.
        north_m = (bounds.lat_max - bounds.lat_min) * 111195 / 2
        east_m = (bounds.lng_max - bounds.lng_min) * 111195 * cos(radians(lat)) / 2
        if north_m < 1350 or east_m < 2950:
            raise ValueError(
                f"Planning area too small for OIR circle regression: {bounds}"
            )
        primary = Circle.from_meters(lat, lng, self._RADIUS_M)
        far_lat, far_lng = self._point_at(lat, lng, 2500, 90)
        distant = Circle.from_meters(far_lat, far_lng, 1)
        inside = Circle.from_meters(lat, lng, 200)
        # Sweep the gaps between vertices of the old 20-sided approximation.
        # A single translated point may miss the S2 false-negative regression.
        boundary = []
        for bearing in [264.834626, *range(9, 360, 18)]:
            qlat, qlng = self._point_at(lat, lng, 0.995 * self._RADIUS_M, bearing)
            boundary.append((bearing, Circle.from_meters(qlat, qlng, 1)))
        return primary, boundary, distant, inside

    _dss: DSSInstance

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
    ):
        super().__init__()
        self._planning_area = planning_area
        self._dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "create and query operational intent references"
            }
        )
        self._pid = [self._dss.participant_id]
        self._oir_id = id_generator.id_factory.make_id(self.OIR_TYPE)
        self._created_oir = None

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self._cleanup_known_oir("Clear previous test OIR")
        self.end_test_case()

        self.begin_test_case("Discover an OIR through an overlapping circle")
        primary, boundary, distant, inside = self._circles()
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=60)
        self.begin_test_step("Create large circular OIR")
        params = PutOperationalIntentReferenceParameters(
            extents=[
                Volume4D.from_values(
                    t0=start, t1=end, alt0=30, alt1=120, circle=primary
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

        # A: Catch the original S2 boundary false negative from any direction.
        self.begin_test_step("Boundary overlap is discoverable")
        for bearing, circle in boundary:
            self._search(
                "Boundary overlap is discoverable",
                circle,
                start,
                end,
                30,
                120,
                True,
                bearing,
            )
        self.end_test_step()

        # B–E: Negative controls and an ordinary positive control.
        cases = [
            ("Distant circle does not match", distant, start, end, 30, 120, False),
            (
                "Disjoint altitude does not match",
                boundary[0][1],
                start,
                end,
                250,
                350,
                False,
            ),
            (
                "Disjoint time does not match",
                boundary[0][1],
                end + timedelta(minutes=10),
                end + timedelta(minutes=40),
                30,
                120,
                False,
            ),
            (
                "Ordinary contained circle is discoverable",
                inside,
                start,
                end,
                30,
                120,
                True,
            ),
        ]
        for title, circle, t0, t1, alt0, alt1, expected in cases:
            self.begin_test_step(title)
            self._search(title, circle, t0, t1, alt0, alt1, expected)
            self.end_test_step()

        self.begin_test_step("Delete large circular OIR")
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

    def _search(self, title, circle, t0, t1, alt0, alt1, expected, bearing=None):
        query = Volume4D.from_values(
            t0=t0, t1=t1, alt0=alt0, alt1=alt1, circle=circle
        ).to_f3548v21()
        with self.check(title, self._pid) as check:
            try:
                found, response = self._dss.find_op_intent(query)
                self.record_query(response)
                ids = {oir.id for oir in found}
                if (self._oir_id in ids) != expected:
                    check.record_failed(
                        summary=(
                            "Overlapping OIR was missing"
                            if expected
                            else "OIR was returned for a disjoint 4D query"
                        ),
                        details=(
                            f"Case: {title}; bearing={bearing}; expected_found={expected}; "
                            f"expected_id={self._oir_id}; returned_ids={sorted(ids)}; "
                            f"query_circle={circle}; query_time=[{t0}, {t1}]; "
                            f"query_altitude_m=[{alt0}, {alt1}]"
                        ),
                        query_timestamps=[response.request.timestamp],
                    )
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary=f"Search failed: {title}",
                    details=f"HTTP {e.cause_status_code}: {e.msg}",
                    query_timestamps=e.query_timestamps,
                )

    def _cleanup_known_oir(self, name: str):
        self.begin_test_step(name)
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_test_step()

    def cleanup(self):
        self.begin_cleanup()
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_cleanup()

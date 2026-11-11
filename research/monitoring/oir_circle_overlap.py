"""API regression for circular OIR overlap at the S2 covering boundary."""

from datetime import UTC, datetime, timedelta

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

    # Fixtures verified by Go's actual old 20-gon and fixed S2 Cap covering.
    # Keep this table explicit: unverified coordinates must never silently PASS.
    _FIXTURES = (
        ("kentland", 37.1853, -80.6140,
         37.1925500000, -80.5598000000, 37.1974823562, -80.5549020408),
        ("east10km", 37.1853, -80.6140 + 10000 / (111195 * 0.797),
         37.1938000000, -80.4725617299, 37.1902924429, -80.4660090559),
        ("south10km", 37.1853 - 10000 / 111195, -80.6140,
         37.1026178987, -80.5582000000, 37.1026541287, -80.5660772463),
    )

    def _circles(self):
        bounds = self._planning_area.get_extents()
        for name, min_lat, min_lng, lat, lng, query_lat, query_lng in self._FIXTURES:
            if abs(bounds.lat_min - min_lat) > 0.0001 or abs(bounds.lng_min - min_lng) > 0.0001:
                continue
            # The 1m query circle must remain within the registered 700m circle.
            primary = Circle.from_meters(lat, lng, 700)
            boundary = [(name, Circle.from_meters(query_lat, query_lng, 1))]
            distant = Circle.from_meters(lat, lng + 0.03, 1)
            inside = Circle.from_meters(lat, lng, 200)
            return primary, boundary, distant, inside
        raise ValueError(
            f"No Go-verified S2 boundary fixture for planning area {bounds}"
        )

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

        # A: Detect the old S2 false negative using a Go-verified fixture.
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

"""API regression for circular OIR overlap at the S2 covering boundary."""

from datetime import UTC, datetime, timedelta
from math import asin, atan2, cos, degrees, radians, sin

import s2sphere
from shapely.geometry import Polygon

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

    _EARTH_RADIUS_M = 6371010.0

    @staticmethod
    def _point_at(lat, lng, meters, bearing):
        """Move along a great-circle bearing, in meters."""
        lat1, lng1, angle = radians(lat), radians(lng), meters / 6371010.0
        theta = radians(bearing)
        lat2 = asin(sin(lat1) * cos(angle) + cos(lat1) * sin(angle) * cos(theta))
        lng2 = lng1 + atan2(
            sin(theta) * sin(angle) * cos(lat1),
            cos(angle) - sin(lat1) * sin(lat2),
        )
        return degrees(lat2), degrees(lng2)

    def _circles(self):
        """Find a boundary query whose entire S2 footprint misses the old 20-gon."""
        bounds = self._planning_area.get_extents()
        mid_lat = (bounds.lat_min + bounds.lat_max) / 2
        mid_lng = (bounds.lng_min + bounds.lng_max) / 2

        # Use S2 cells for all 1m query positions, not just the center cell.
        # Otherwise a nearby cell may make the old implementation pass.
        def cells_of_circle(lat, lng):
            cells = set()
            for bearing in range(0, 360, 30):
                p_lat, p_lng = self._point_at(lat, lng, 1, bearing)
                cells.add(
                    s2sphere.CellId.from_lat_lng(
                        s2sphere.LatLng.from_degrees(p_lat, p_lng)
                    ).parent(13).id()
                )
            cells.add(
                s2sphere.CellId.from_lat_lng(
                    s2sphere.LatLng.from_degrees(lat, lng)
                ).parent(13).id()
            )
            return cells

        for i in range(-9, 10):
            for j in range(-12, 13):
                lat = mid_lat + i * 0.00125
                lng = mid_lng + j * 0.00175
                meters_lat = 111195.0
                meters_lng = meters_lat * cos(radians(lat))
                for radius in (700, 900, 1100, 1300):
                    clearance = min(
                        (lat - bounds.lat_min) * meters_lat,
                        (bounds.lat_max - lat) * meters_lat,
                        (lng - bounds.lng_min) * meters_lng,
                        (bounds.lng_max - lng) * meters_lng,
                    )
                    if clearance < radius + 20:
                        continue

                    def xy(v_lat, v_lng):
                        return v_lng * meters_lng, v_lat * meters_lat

                    old = Polygon(
                        [
                            xy(*self._point_at(lat, lng, radius, bearing))
                            for bearing in range(0, 360, 18)
                        ]
                    )
                    cache = {}
                    for fraction in (0.99, 0.995, 0.998):
                        for bearing in range(0, 360, 3):
                            qlat, qlng = self._point_at(
                                lat, lng, radius * fraction, bearing
                            )
                            query_cells = cells_of_circle(qlat, qlng)
                            excluded = True
                            for cell_id in query_cells:
                                if cell_id not in cache:
                                    cell = s2sphere.Cell(s2sphere.CellId(cell_id))
                                    vertices = [
                                        s2sphere.LatLng.from_point(
                                            cell.get_vertex(k)
                                        )
                                        for k in range(4)
                                    ]
                                    cache[cell_id] = Polygon(
                                        [
                                            xy(v.lat().degrees, v.lng().degrees)
                                            for v in vertices
                                        ]
                                    )
                                if cache[cell_id].intersects(old):
                                    excluded = False
                                    break
                            if not excluded:
                                continue

                            # Pick a control far enough away, but still in the area.
                            distant = None
                            for direction in (0, 90, 180, 270):
                                f_lat, f_lng = self._point_at(lat, lng, 2500, direction)
                                if (
                                    bounds.lat_min < f_lat < bounds.lat_max
                                    and bounds.lng_min < f_lng < bounds.lng_max
                                ):
                                    distant = Circle.from_meters(f_lat, f_lng, 1)
                                    break
                            if distant is None:
                                continue
                            return (
                                Circle.from_meters(lat, lng, radius),
                                [(bearing, Circle.from_meters(qlat, qlng, 1))],
                                distant,
                                Circle.from_meters(lat, lng, 200),
                            )
        raise ValueError(
            f"No robust S2 regression fixture fits planning area {bounds}"
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

        # A: Catch a small boundary overlap omitted by the old polygon.
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

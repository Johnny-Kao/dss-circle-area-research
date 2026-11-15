"""DSS circular OIR boundary search — independent research candidate.

DSS search correctness is judged by real 4D overlap only. S2 Cell edges
are used to select an implementation-independent boundary search fixture.
"""

from datetime import UTC, datetime, timedelta
from math import cos, pi, sin

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
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstanceResource,
)
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.dss.fragments.oir import (
    crud as oir_fragments,
)
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class FixtureUnavailable(Exception):
    """No valid, diagnostically useful cross-cell circles fit this planning area."""


class OIRCircleOverlap(TestScenario):
    """A search overlapping an OIR must discover it, even across a cell boundary."""

    OIR_TYPE = register_resource_type(407, "Circular overlap operational intent")
    EARTH_RADIUS_M = 6371010.0
    CELL_LEVEL = 13
    QUERY_RADIUS_M = 1.0
    OIR_RADII_M = (200.0, 150.0, 100.0)
    SAMPLE_FRACTIONS = tuple(i / 8 for i in range(1, 8))

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

    @staticmethod
    def _move(origin, tangent, meters):
        theta = meters / OIRCircleOverlap.EARTH_RADIUS_M
        return (origin * cos(theta) + tangent * sin(theta)).normalize()

    @staticmethod
    def _latlng(point):
        ll = s2sphere.LatLng.from_point(point)
        return ll.lat().degrees, ll.lng().degrees

    @classmethod
    def _ring(cls, center, radius, count):
        y_axis = s2sphere.ortho(center)
        x_axis = y_axis.cross_prod(center).normalize()
        theta = radius / cls.EARTH_RADIUS_M
        return [
            (
                center * cos(theta)
                + x_axis * (sin(theta) * cos(2 * pi * k / count))
                + y_axis * (sin(theta) * sin(2 * pi * k / count))
            ).normalize()
            for k in range(count)
        ]

    @classmethod
    def _cell(cls, point):
        return s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_point(point)).parent(
            cls.CELL_LEVEL
        )

    @classmethod
    def _fits(cls, center, radius, volume, reference):
        if volume.outline_circle is not None:
            source = volume.outline_circle
            if source.radius.units != "M":
                raise ValueError("Planning area requires meter radii")
            center_point = s2sphere.LatLng.from_degrees(
                source.center.lat, source.center.lng
            ).to_point()
            return (
                center.angle(center_point) * cls.EARTH_RADIUS_M + radius + 1
                < source.radius.value
            )
        if volume.outline_polygon is None:
            raise ValueError("Planning area needs a circle or polygon outline")
        polygon = Polygon(
            flatten(reference, v.as_s2sphere()) for v in volume.outline_polygon.vertices
        )
        if not polygon.is_valid or polygon.is_empty:
            raise ValueError("Invalid planning area geometry")
        return polygon.buffer(-(radius + 1)).covers(
            Point(*flatten(reference, s2sphere.LatLng.from_point(center)))
        )

    @staticmethod
    def _altitudes(volume):
        low = (
            volume.altitude_lower_wgs84_m()
            if volume.altitude_lower is not None
            else None
        )
        high = (
            volume.altitude_upper_wgs84_m()
            if volume.altitude_upper is not None
            else None
        )
        if low is None and high is None:
            low, high = 30.0, 120.0
        elif low is None:
            low = high - 90.0
        elif high is None:
            high = low + 90.0
        if low >= high:
            raise FixtureUnavailable("No positive altitude span")
        return low + (high - low) / 4, high - (high - low) / 4

    def _fixture(self, volume):
        bounds = self._planning_area.get_extents()
        lat = (bounds.lat_min + bounds.lat_max) / 2
        lng = (bounds.lng_min + bounds.lng_max) / 2
        reference = s2sphere.LatLng.from_degrees(lat, lng)
        direction = reference.to_point()
        candidate_cells = {}
        for x in self.SAMPLE_FRACTIONS:
            for y in self.SAMPLE_FRACTIONS:
                sample = s2sphere.LatLng.from_degrees(
                    bounds.lat_min + (bounds.lat_max - bounds.lat_min) * x,
                    bounds.lng_min + (bounds.lng_max - bounds.lng_min) * y,
                ).to_point()
                cell_id = self._cell(sample)
                candidate_cells[cell_id.id()] = cell_id

        for cell_id in sorted(candidate_cells.values(), key=lambda c: c.id()):
            cell = s2sphere.Cell(cell_id)
            neighbors = set(cell_id.get_edge_neighbors())
            for edge in range(4):
                a, b = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
                inward = a.cross_prod(b).normalize()
                if inward.dot_prod(cell.get_center()) < 0:
                    inward = -inward
                boundary = (direction - inward * inward.dot_prod(direction)).normalize()
                if abs(a.angle(boundary) + boundary.angle(b) - a.angle(b)) > 1e-7:
                    boundary = (a + b).normalize()

                for radius in self.OIR_RADII_M:
                    # Place B entirely in the neighboring Cell while A crosses
                    # the Cell boundary with 0.5 m of real circular overlap.
                    y = self.QUERY_RADIUS_M + 0.01
                    x = radius - 0.51
                    if x + y >= radius + self.QUERY_RADIUS_M - 0.01:
                        continue
                    primary = self._move(boundary, inward, x)
                    query = self._move(boundary, -inward, y)
                    query_cell = self._cell(query)
                    if self._cell(primary) != cell_id or query_cell not in neighbors:
                        continue
                    if any(
                        self._cell(point) != query_cell
                        for point in self._ring(query, self.QUERY_RADIUS_M, 24)
                    ):
                        continue
                    if not (
                        self._fits(primary, radius, volume, reference)
                        and self._fits(query, self.QUERY_RADIUS_M, volume, reference)
                    ):
                        continue
                    overlap = (
                        radius
                        + self.QUERY_RADIUS_M
                        - primary.angle(query) * self.EARTH_RADIUS_M
                    )
                    if overlap <= 0.01:
                        continue
                    self.record_note(
                        "fixture_constructed",
                        f"radius_m={radius}; overlap_m={overlap:.3f}; "
                        f"cell={cell_id.id()}",
                    )
                    return (
                        Circle.from_meters(*self._latlng(primary), radius),
                        Circle.from_meters(*self._latlng(query), self.QUERY_RADIUS_M),
                    )
        raise FixtureUnavailable(
            f"No valid cross-cell circular overlap within {bounds}"
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        volume = self._planning_area.resolved_volume4d_with_times(None, None).volume
        try:
            alt0, alt1 = self._altitudes(volume)
            primary, query_circle = self._fixture(volume)
        except FixtureUnavailable as e:
            self.record_note("test_inapplicable", str(e))
            self.end_test_scenario()
            return
        self.begin_test_case("Setup")
        self.begin_test_step("Clear previous test OIR")
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Overlapping circular OIR is discoverable")
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=60)
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
        query = Volume4D.from_values(
            t0=start, t1=end, alt0=alt0, alt1=alt1, circle=query_circle
        ).to_f3548v21()
        with self.check(
            "Boundary overlap is discoverable", self._participants
        ) as check:
            try:
                found, response = self._dss.find_op_intent(query)
                self.record_query(response)
                if self._oir_id not in {oir.id for oir in found}:
                    check.record_failed(
                        summary="Overlapping OIR was missing",
                        details=f"OIR id={self._oir_id}; query={query_circle}",
                        query_timestamps=[response.request.timestamp],
                    )
            except QueryError as e:
                self.record_queries(e.queries)
                check.record_failed(
                    summary="Search failed",
                    details=f"HTTP {e.cause_status_code}: {e.msg}",
                    query_timestamps=e.query_timestamps,
                )
        self.end_test_step()

        self.begin_test_step("Delete circular OIR")
        oir_fragments.delete_oir_query(
            scenario=self, dss=self._dss, oir_id=self._oir_id, ovn=self._created_oir.ovn
        )
        self._created_oir = None
        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_cleanup()

"""Test discovery of registered circular OIRs through the DSS search API."""

from datetime import UTC, datetime, timedelta
from itertools import product
from math import cos, sin

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
    """No valid overlapping query can be placed within the planning area."""


class OIRCircleOverlap(TestScenario):
    """Check discovery of operational intent references through circular queries."""

    OIR_TYPE = register_resource_type(
        407, "Circular overlap operational intent reference"
    )
    EARTH_RADIUS_M = 6371010.0
    CELL_LEVEL = 13
    QUERY_RADIUS_M = 1.0
    OIR_RADII_M = (300.0, 250.0, 200.0)
    OVERLAP_DEPTHS_M = (1.5,)
    MAX_FIXTURES = 4
    SAMPLE_FRACTIONS = tuple(i / 8 for i in range(1, 8))

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        planning_area: PlanningAreaResource,
    ):
        super().__init__()
        self._dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "create and query operational intent references"
            }
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
    def _circle_in_cell(cls, cell, center, radius):
        """Check that the entire query circle is contained within an S2 cell."""
        if not cell.contains(center):
            return False
        clearance = sin(radius / cls.EARTH_RADIUS_M)
        for i in range(4):
            a, b = cell.get_vertex(i), cell.get_vertex((i + 1) % 4)
            inward = a.cross_prod(b).normalize()
            if inward.dot_prod(cell.get_center()) < 0:
                inward = -inward
            if inward.dot_prod(center) <= clearance:
                return False
        return True

    @classmethod
    def _cell(cls, point):
        return s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_point(point)).parent(
            cls.CELL_LEVEL
        )

    @classmethod
    def _fits(cls, center, radius, volume, reference):
        """Check whether a candidate circle fits within the planning area."""
        if volume.outline_circle is not None:
            source = volume.outline_circle
            center_point = s2sphere.LatLng.from_degrees(
                source.center.lat, source.center.lng
            ).to_point()
            return (
                center.angle(center_point) * cls.EARTH_RADIUS_M + radius + 1
                < source.radius.in_meters()
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
    def _altitudes(area):
        """Choose an altitude interval inside the configured planning area."""
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

    def _fixtures(self, volume):
        """Build genuine circle overlaps without assuming a DSS index design."""
        bounds = self._planning_area.get_extents()
        lat = (bounds.lat_min + bounds.lat_max) / 2
        lng = (bounds.lng_min + bounds.lng_max) / 2
        reference = s2sphere.LatLng.from_degrees(lat, lng)
        direction = reference.to_point()

        cells = {}
        for fx, fy in product(self.SAMPLE_FRACTIONS, repeat=2):
            longitude = (
                bounds.lng_min + (bounds.lng_max - bounds.lng_min) * fy + 180
            ) % 360 - 180
            sample = s2sphere.LatLng.from_degrees(
                bounds.lat_min + (bounds.lat_max - bounds.lat_min) * fx,
                longitude,
            ).to_point()
            cid = self._cell(sample)
            cells[cid.id()] = cid

        # S2 cell edges guide test placement only; DSS behavior is checked via
        # the API against the actual circular overlap.
        fixtures = []
        for cell_id in sorted(cells.values(), key=lambda c: c.id()):
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
                positions = (
                    boundary,
                    (a + b).normalize(),
                    (a * 3 + b).normalize(),
                    (a + b * 3).normalize(),
                )
                for position, radius, depth in product(
                    positions, self.OIR_RADII_M, self.OVERLAP_DEPTHS_M
                ):
                    primary = self._move(position, inward, radius - depth - 0.01)
                    query = self._move(position, -inward, self.QUERY_RADIUS_M + 0.01)
                    query_cell = self._cell(query)
                    if self._cell(primary) != cell_id or query_cell not in neighbors:
                        continue
                    if not self._circle_in_cell(
                        s2sphere.Cell(query_cell), query, self.QUERY_RADIUS_M
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
                    if abs(overlap - depth) > 0.001:
                        continue
                    fixtures.append(
                        (
                            Circle.from_meters(*self._latlng(primary), radius),
                            Circle.from_meters(
                                *self._latlng(query), self.QUERY_RADIUS_M
                            ),
                        )
                    )
                    self.record_note(
                        "fixture_constructed",
                        f"cell={cell_id.id()}; edge={edge}; "
                        f"radius_m={radius}; overlap_m={overlap:.3f}",
                    )
                    if len(fixtures) == self.MAX_FIXTURES:
                        return fixtures
        if fixtures:
            return fixtures
        raise FixtureUnavailable(
            f"No legal cross-cell circle overlap within PlanningAreaResource {bounds}"
        )

    def _check_found(self, name, circle, start, end, alt0, alt1):
        """Verify that a positive search result includes the registered OIR."""
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
        for primary, query_circle in fixtures:
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
            self._check_found(
                "Boundary overlap is discoverable",
                query_circle,
                start,
                end,
                alt0,
                alt1,
            )
            self.end_test_step()

            self.begin_test_step("Ordinary contained circle discovers OIR")
            inside = Circle.from_meters(
                primary.center.lat, primary.center.lng, primary.radius.value / 2
            )
            self._check_found(
                "Ordinary contained circle discovers OIR",
                inside,
                start,
                end,
                alt0,
                alt1,
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

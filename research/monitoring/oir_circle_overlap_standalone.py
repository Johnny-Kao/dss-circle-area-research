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
from monitoring.monitorlib.geo import EARTH_RADIUS_M, Circle, flatten
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.ids import register_resource_type
from monitoring.monitorlib.s2 import cell_of
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
    """No valid cross-boundary circular fixture fits in the planning area."""


class OIRCircleOverlap(TestScenario):
    """Check discovery of OIRs through genuinely overlapping circular queries."""

    OIR_TYPE = register_resource_type(
        407, "Circular overlap operational intent reference"
    )

    # S2 is used only to place a difficult boundary geometry.  The assertion is
    # implementation-independent: a genuinely intersecting OIR must be returned.
    CELL_LEVEL = 13
    OIR_RADIUS_M = 200.0
    QUERY_RADIUS_M = 1.0
    # Keep the overlap deliberately small so this remains a sharp boundary case.
    OIR_CROSSING_DEPTH_M = 0.11
    QUERY_BOUNDARY_CLEARANCE_M = 0.01
    PLANNING_AREA_MARGIN_M = 1.0
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

    @staticmethod
    def _move(origin, tangent, meters):
        theta = meters / EARTH_RADIUS_M
        return (origin * cos(theta) + tangent * sin(theta)).normalize()

    @classmethod
    def _cell(cls, point):
        ll = s2sphere.LatLng.from_point(point)
        return cell_of(ll.lat().degrees, ll.lng().degrees, cls.CELL_LEVEL)

    @staticmethod
    def _edge(cell, edge):
        a = cell.get_vertex(edge)
        b = cell.get_vertex((edge + 1) % 4)
        boundary = (a + b).normalize()
        inward = a.cross_prod(b).normalize()
        if inward.dot_prod(cell.get_center()) < 0:
            inward = -inward
        return boundary, inward

    @classmethod
    def _circle_in_cell(cls, cell, center, radius_m):
        if not cell.contains(center):
            return False
        clearance = sin(radius_m / EARTH_RADIUS_M)
        for edge in range(4):
            a = cell.get_vertex(edge)
            b = cell.get_vertex((edge + 1) % 4)
            inward = a.cross_prod(b).normalize()
            if inward.dot_prod(cell.get_center()) < 0:
                inward = -inward
            if inward.dot_prod(center) <= clearance:
                return False
        return True

    @staticmethod
    def _reference(volume):
        if volume.outline_circle is not None:
            return volume.outline_circle.center.as_s2sphere()
        if volume.outline_polygon is not None and volume.outline_polygon.vertices:
            return volume.outline_polygon.vertex_average().as_s2sphere()
        raise FixtureUnavailable("Planning Area needs a circle or polygon outline")

    @classmethod
    def _fits(cls, center, radius_m, volume, reference):
        margin = cls.PLANNING_AREA_MARGIN_M
        if volume.outline_circle is not None:
            planning_center = volume.outline_circle.center.as_s2sphere().to_point()
            distance = center.angle(planning_center) * EARTH_RADIUS_M
            return (
                distance + radius_m + margin < volume.outline_circle.radius.in_meters()
            )

        polygon = Polygon(
            flatten(reference, vertex.as_s2sphere())
            for vertex in volume.outline_polygon.vertices
        )
        if not polygon.is_valid or polygon.is_empty:
            raise FixtureUnavailable("Planning Area polygon is invalid")
        candidate = Point(*flatten(reference, s2sphere.LatLng.from_point(center)))
        return polygon.buffer(-(radius_m + margin)).covers(candidate)

    @staticmethod
    def _altitudes(area):
        low = area.altitude_lower_wgs84_m() if area.altitude_lower else None
        high = area.altitude_upper_wgs84_m() if area.altitude_upper else None
        if low is None:
            low = high - 90.0 if high is not None else 30.0
        if high is None:
            high = low + 90.0
        if low >= high:
            raise FixtureUnavailable("Planning Area has no positive altitude span")
        return low + (high - low) / 4, high - (high - low) / 4

    @staticmethod
    def _circle(center, radius_m):
        ll = s2sphere.LatLng.from_point(center)
        return Circle.from_meters(ll.lat().degrees, ll.lng().degrees, radius_m)

    def _fixtures(self, volume):
        """Select up to four small, true-circle overlaps on distinct S2 edge axes."""
        bounds = self._planning_area.get_extents()
        reference_ll = self._reference(volume)
        cells = {}
        for fx, fy in product(self.SAMPLE_FRACTIONS, repeat=2):
            sample = s2sphere.LatLng.from_degrees(
                bounds.lat_min + (bounds.lat_max - bounds.lat_min) * fx,
                bounds.lng_min + (bounds.lng_max - bounds.lng_min) * fy,
            ).to_point()
            cell_id = self._cell(sample)
            cells[cell_id.id()] = cell_id

        # Sampling all four edge directions avoids depending on just the first
        # usable edge, which can be uninformative in a valid planning area.
        selected = {}
        for cell_id in sorted(cells.values(), key=lambda c: c.id()):
            cell = s2sphere.Cell(cell_id)
            neighbors = set(cell_id.get_edge_neighbors())
            for edge in range(4):
                if edge in selected:
                    continue
                boundary, inward = self._edge(cell, edge)
                oir_center = self._move(
                    boundary,
                    inward,
                    self.OIR_RADIUS_M - self.OIR_CROSSING_DEPTH_M,
                )
                query_center = self._move(
                    boundary,
                    -inward,
                    self.QUERY_RADIUS_M + self.QUERY_BOUNDARY_CLEARANCE_M,
                )
                query_id = self._cell(query_center)
                if self._cell(oir_center) != cell_id or query_id not in neighbors:
                    continue
                if not self._circle_in_cell(
                    s2sphere.Cell(query_id), query_center, self.QUERY_RADIUS_M
                ):
                    continue
                if not self._fits(
                    oir_center, self.OIR_RADIUS_M, volume, reference_ll
                ) or not self._fits(
                    query_center, self.QUERY_RADIUS_M, volume, reference_ll
                ):
                    continue
                overlap = (
                    self.OIR_RADIUS_M
                    + self.QUERY_RADIUS_M
                    - oir_center.angle(query_center) * EARTH_RADIUS_M
                )
                expected = self.OIR_CROSSING_DEPTH_M - self.QUERY_BOUNDARY_CLEARANCE_M
                if overlap <= 0 or abs(overlap - expected) > 0.001:
                    continue

                selected[edge] = (
                    self._circle(oir_center, self.OIR_RADIUS_M),
                    self._circle(query_center, self.QUERY_RADIUS_M),
                )
                self.record_note(
                    "fixture_constructed",
                    f"source_cell={cell_id.id()}; query_cell={query_id.id()}; "
                    f"edge={edge}; overlap_m={overlap:.3f}",
                )
            if len(selected) == 4:
                break

        if not selected:
            raise FixtureUnavailable(
                f"No valid boundary-overlap fixture in PlanningAreaResource {bounds}"
            )
        return [selected[edge] for edge in sorted(selected)]

    def _check_found(self, name, circle, start, end, alt0, alt1):
        query = Volume4D.from_values(
            t0=start,
            t1=end,
            alt0=alt0,
            alt1=alt1,
            circle=circle,
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

        for oir_circle, boundary_query in fixtures:
            self.begin_test_step("Create circular OIR")
            params = PutOperationalIntentReferenceParameters(
                extents=[
                    Volume4D.from_values(
                        t0=start,
                        t1=end,
                        alt0=alt0,
                        alt1=alt1,
                        circle=oir_circle,
                    ).to_f3548v21()
                ],
                key=[],
                state=OperationalIntentState.Accepted,
                uss_base_url=make_fake_url(),
                subscription_id=None,
            )
            created_oir, _, _ = oir_fragments.create_oir_query(
                scenario=self,
                dss=self._dss,
                oir_id=self._oir_id,
                oir_params=params,
            )
            self.end_test_step()

            self.begin_test_step("Discover boundary-overlapping OIR")
            self._check_found(
                "Boundary overlap is discoverable",
                boundary_query,
                start,
                end,
                alt0,
                alt1,
            )
            self.end_test_step()

            self.begin_test_step("Ordinary contained circle discovers OIR")
            contained_query = Circle.from_meters(
                oir_circle.center.lat,
                oir_circle.center.lng,
                self.OIR_RADIUS_M / 2,
            )
            self._check_found(
                "Ordinary contained circle discovers OIR",
                contained_query,
                start,
                end,
                alt0,
                alt1,
            )
            self.end_test_step()

            self.begin_test_step("Delete circular OIR")
            assert created_oir.ovn is not None
            oir_fragments.delete_oir_query(
                scenario=self,
                dss=self._dss,
                oir_id=self._oir_id,
                ovn=created_oir.ovn,
            )
            self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def cleanup(self):
        self.begin_cleanup()
        test_step_fragments.cleanup_op_intent(self, self._dss, self._oir_id)
        self.end_cleanup()

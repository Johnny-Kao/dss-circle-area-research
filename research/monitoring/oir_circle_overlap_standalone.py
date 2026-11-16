"""Test discovery of registered circular OIRs through the DSS search API."""

from datetime import UTC, datetime, timedelta
from itertools import product
from math import cos, pi, sin

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
    EDGE_FRACTIONS = (0.25, 0.5, 0.75)
    CIRCLE_RADII_M = (200.0, 150.0, 100.0)
    CROSSING_DEPTHS_M = (0.11, 0.25)

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

    @classmethod
    def _old_index_witness(cls, center, radius_m, source_id):
        """Require the historical inscribed footprint to remain in one S2 cell.

        This selects a difficult input, not an API expectation. DSS conformance
        depends only on true 4D intersection and the actual search response.
        """
        # Match the orientation of S2 RegularLoop's tangent frame. This
        # fingerprint of the historical bug is *only* a fixture filter.
        circular = cls._circle(center, radius_m)
        point = circular.center.as_s2sphere().to_point()
        values = (abs(point.x), abs(point.y), abs(point.z))
        tangent = [0.012, 0.0053, 0.00457]
        dominant = values.index(max(values))
        tangent[(dominant + 2) % 3] = 1.0
        y = point.cross_prod(s2sphere.Point(*tangent)).normalize()
        x = y.cross_prod(point).normalize()

        # Historical DSS used a 20-vertex inscribed S2 RegularLoop with the
        # S2 Go library's spherical radius. The actual registered OIR remains
        # a *circle*; no polygon is submitted to or expected from any DSS.
        theta = radius_m / 6371010.0
        for i in range(20):
            a = 2 * pi * i / 20
            vertex = (
                x * (sin(theta) * cos(a))
                + y * (sin(theta) * sin(a))
                + point * cos(theta)
            ).normalize()
            if cls._cell(vertex) != source_id:
                return False
        return True

    def _fixtures(self, volume):
        """Construct four genuinely intersecting, index-adversarial circle pairs."""
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

        selected = {}
        for cell_id in sorted(cells.values(), key=lambda c: c.id()):
            cell = s2sphere.Cell(cell_id)
            neighbors = set(cell_id.get_edge_neighbors())
            for edge in range(4):
                if edge in selected:
                    continue
                a, b = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
                inward = a.cross_prod(b).normalize()
                if inward.dot_prod(cell.get_center()) < 0:
                    inward = -inward
                for fraction in self.EDGE_FRACTIONS:
                    boundary = (a * (1 - fraction) + b * fraction).normalize()
                    query_center = self._move(
                        boundary,
                        -inward,
                        self.QUERY_RADIUS_M + self.QUERY_BOUNDARY_CLEARANCE_M,
                    )
                    query_id = self._cell(query_center)
                    if query_id not in neighbors:
                        continue
                    if not self._circle_in_cell(
                        s2sphere.Cell(query_id), query_center, self.QUERY_RADIUS_M
                    ) or not self._fits(
                        query_center, self.QUERY_RADIUS_M, volume, reference_ll
                    ):
                        continue
                    for radius_m, depth_m in product(
                        self.CIRCLE_RADII_M, self.CROSSING_DEPTHS_M
                    ):
                        oir_center = self._move(
                            boundary, inward, radius_m - depth_m
                        )
                        if self._cell(oir_center) != cell_id:
                            continue
                        if not self._fits(
                            oir_center, radius_m, volume, reference_ll
                        ):
                            continue
                        overlap = (
                            radius_m
                            + self.QUERY_RADIUS_M
                            - oir_center.angle(query_center) * EARTH_RADIUS_M
                        )
                        if overlap <= 0 or abs(
                            overlap - (depth_m - self.QUERY_BOUNDARY_CLEARANCE_M)
                        ) > 0.005:
                            continue
                        # The inscribed historic index must remain in the
                        # source cell while the real circle reaches the query.
                        if not self._old_index_witness(
                            oir_center, radius_m, cell_id
                        ):
                            continue
                        selected[edge] = (
                            self._circle(oir_center, radius_m),
                            self._circle(query_center, self.QUERY_RADIUS_M),
                        )
                        self.record_note(
                            "fixture_constructed",
                            f"source_cell={cell_id.id()}; query_cell={query_id.id()}; "
                            f"edge={edge}; overlap_m={overlap:.3f}",
                        )
                        break
                    if edge in selected:
                        break
            if len(selected) == 4:
                break

        if len(selected) != 4:
            missing = sorted(set(range(4)) - set(selected))
            raise FixtureUnavailable(
                f"PlanningAreaResource {bounds} cannot fit four adversarial "
                f"S2 edge orientations; missing edges: {missing}"
            )
        return [selected[edge] for edge in range(4)]

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
                oir_circle.radius.in_meters() / 2,
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

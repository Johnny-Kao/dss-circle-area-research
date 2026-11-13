"""API regression for circular OIR overlap at the S2 covering boundary."""

from datetime import UTC, datetime, timedelta
from math import cos, pi, sin

import s2sphere

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
    _S2_CELL_LEVEL = 13
    _QUERY_RADIUS_M = 1.0
    _INSIDE_QUERY_RADIUS_M = 50.0
    _LEGACY_POLYGON_VERTICES = 20
    _CIRCLE_CONFIGURATIONS = ((200.0, 0.75, 1.25), (150.0, 0.50, 1.20), (100.0, 0.25, 1.10), (80.0, 0.10, 1.05))
    _EDGE_FRACTIONS = tuple(i / 10 for i in range(1, 10))
    _AREA_SAMPLE_FRACTIONS = tuple(i / 8 for i in range(1, 8))

    @staticmethod
    def _point_to_lat_lng(point):
        ll = s2sphere.LatLng.from_point(point)
        return ll.lat().degrees, ll.lng().degrees

    @classmethod
    def _move_point(cls, origin, tangent, meters):
        angle = meters / cls._EARTH_RADIUS_M
        return (origin * cos(angle) + tangent * sin(angle)).normalize()

    @staticmethod
    def _interpolate_edge(a, b, fraction):
        angle = a.angle(b)
        if angle == 0:
            return a
        return (a * (sin((1-fraction)*angle)/sin(angle)) + b * (sin(fraction*angle)/sin(angle))).normalize()

    @classmethod
    def _ring_points(cls, center, radius_m, count=24):
        y_axis = s2sphere.ortho(center)
        x_axis = y_axis.cross_prod(center).normalize()
        angle = radius_m / cls._EARTH_RADIUS_M
        return [(x_axis * (sin(angle)*cos(2*pi*i/count)) + y_axis * (sin(angle)*sin(2*pi*i/count)) + center * cos(angle)).normalize() for i in range(count)]

    @classmethod
    def _legacy_vertices(cls, center, radius_m):
        return cls._ring_points(center, radius_m, cls._LEGACY_POLYGON_VERTICES)

    @classmethod
    def _cell_id(cls, point):
        return s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_point(point)).parent(cls._S2_CELL_LEVEL)

    @classmethod
    def _inside_bounds(cls, point, bounds):
        lat, lng = cls._point_to_lat_lng(point)
        return bounds.lat_min < lat < bounds.lat_max and bounds.lng_min < lng < bounds.lng_max

    @classmethod
    def _circle_inside_bounds(cls, center, radius, bounds):
        return cls._inside_bounds(center, bounds) and all(cls._inside_bounds(p, bounds) for p in cls._ring_points(center, radius))

    def _candidate_cells(self, bounds):
        cells = {}
        for a in self._AREA_SAMPLE_FRACTIONS:
            for b in self._AREA_SAMPLE_FRACTIONS:
                lat = bounds.lat_min + (bounds.lat_max-bounds.lat_min)*a
                lng = bounds.lng_min + (bounds.lng_max-bounds.lng_min)*b
                cid = s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(lat,lng)).parent(self._S2_CELL_LEVEL)
                cells[cid.id()] = cid
        return [cells[k] for k in sorted(cells)]

    def _circles(self):
        bounds = self._planning_area.get_extents()
        for cid in self._candidate_cells(bounds):
            cell = s2sphere.Cell(cid)
            neighbors = set(cid.get_edge_neighbors())
            for edge in range(4):
                a, b = cell.get_vertex(edge), cell.get_vertex((edge+1)%4)
                inward = a.cross_prod(b).normalize()
                if inward.dot_prod(cell.get_center()) < 0:
                    inward = -inward
                for radius, crossing, offset in self._CIRCLE_CONFIGURATIONS:
                    for fraction in self._EDGE_FRACTIONS:
                        boundary = self._interpolate_edge(a,b,fraction)
                        primary = self._move_point(boundary,inward,radius-crossing)
                        query = self._move_point(boundary,-inward,offset)
                        if self._cell_id(primary) != cid:
                            continue
                        query_cell = self._cell_id(query)
                        if query_cell not in neighbors:
                            continue
                        if not all(self._cell_id(p) == query_cell for p in self._ring_points(query,self._QUERY_RADIUS_M)):
                            continue
                        if not all(cell.contains(v) for v in self._legacy_vertices(primary,radius)):
                            continue
                        if primary.angle(query)*self._EARTH_RADIUS_M >= radius+self._QUERY_RADIUS_M:
                            continue
                        if not self._circle_inside_bounds(primary,radius,bounds) or not self._circle_inside_bounds(query,self._QUERY_RADIUS_M,bounds):
                            continue
                        plat,plng=self._point_to_lat_lng(primary)
                        qlat,qlng=self._point_to_lat_lng(query)
                        return (Circle.from_meters(plat,plng,radius),Circle.from_meters(qlat,qlng,self._QUERY_RADIUS_M),Circle.from_meters(plat,plng,self._INSIDE_QUERY_RADIUS_M))
        raise ValueError(f"Could not construct S2 adversarial geometry inside planning area: {bounds}")

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
        primary, boundary, inside = self._circles()
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=60)
        self.begin_test_step("Create large circular OIR")
        params = PutOperationalIntentReferenceParameters(
            extents=[Volume4D.from_values(t0=start,t1=end,alt0=30,alt1=120,circle=primary).to_f3548v21()],
            key=[],state=OperationalIntentState.Accepted,uss_base_url=make_fake_url(),subscription_id=None,
        )
        self._created_oir, _, _ = oir_fragments.create_oir_query(
            scenario=self,dss=self._dss,oir_id=self._oir_id,oir_params=params
        )
        self.end_test_step()
        self._check_step("Boundary overlap is discoverable",boundary,start,end)
        self._check_step("Ordinary contained circle is discoverable",inside,start,end)
        self.begin_test_step("Delete large circular OIR")
        oir_fragments.delete_oir_query(scenario=self,dss=self._dss,oir_id=self._oir_id,ovn=self._created_oir.ovn)
        self._created_oir=None
        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def _check_step(self, title, circle, t0, t1):
        self.begin_test_step(title)
        self._search(title, circle, t0, t1)
        self.end_test_step()

    def _search(self, title, circle, t0, t1):
        query = Volume4D.from_values(
            t0=t0, t1=t1, alt0=30, alt1=120, circle=circle
        ).to_f3548v21()
        with self.check(title, self._pid) as check:
            try:
                found, response = self._dss.find_op_intent(query)
                self.record_query(response)
                ids = {oir.id for oir in found}
                if self._oir_id not in ids:
                    check.record_failed(
                        summary="Overlapping OIR was missing",
                        details=(
                            f"Case: {title}; expected_id={self._oir_id}; "
                            f"returned_ids={sorted(ids)}; query_circle={circle}; "
                            f"query_time=[{t0}, {t1}]; query_altitude_m=[30, 120]"
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

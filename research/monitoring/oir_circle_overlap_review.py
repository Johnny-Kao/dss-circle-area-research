"""API regression for circular OIR overlap at the S2 covering boundary."""

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


class TestAreaNotApplicable(Exception):
    """Planning Area does not support a meaningful boundary fixture."""


class OIRCircleOverlap(TestScenario):
    """Check that a small circle overlapping the edge of a larger OIR is searchable."""

    OIR_TYPE = register_resource_type(
        407, "Circle overlap operational intent reference"
    )

    _EARTH_RADIUS_M = 6371010.0
    _S2_CELL_LEVEL = 13
    _QUERY_RADIUS_M = 1.0
    _DEFAULT_ALTITUDES_M = (30.0, 120.0)
    _LEGACY_POLYGON_VERTICES = 20
    _OIR_RADIUS_M = 200.0
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
        return (
            a * (sin((1 - fraction) * angle) / sin(angle))
            + b * (sin(fraction * angle) / sin(angle))
        ).normalize()

    @classmethod
    def _ring_points(cls, center, radius_m, count=24):
        y_axis = s2sphere.ortho(center)
        x_axis = y_axis.cross_prod(center).normalize()
        angle = radius_m / cls._EARTH_RADIUS_M
        return [
            (
                x_axis * (sin(angle) * cos(2 * pi * i / count))
                + y_axis * (sin(angle) * sin(2 * pi * i / count))
                + center * cos(angle)
            ).normalize()
            for i in range(count)
        ]

    @classmethod
    def _legacy_vertices(cls, center, radius_m):
        return cls._ring_points(center, radius_m, cls._LEGACY_POLYGON_VERTICES)

    @classmethod
    def _cell_id(cls, point):
        return s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_point(point)).parent(
            cls._S2_CELL_LEVEL
        )

    def _candidate_cells(self, bounds):
        cells = {}
        for a in self._AREA_SAMPLE_FRACTIONS:
            for b in self._AREA_SAMPLE_FRACTIONS:
                lat = bounds.lat_min + (bounds.lat_max - bounds.lat_min) * a
                lng = bounds.lng_min + (bounds.lng_max - bounds.lng_min) * b
                cid = s2sphere.CellId.from_lat_lng(
                    s2sphere.LatLng.from_degrees(lat, lng)
                ).parent(self._S2_CELL_LEVEL)
                cells[cid.id()] = cid
        return [cells[k] for k in sorted(cells)]

    @classmethod
    def _circle_inside_volume(cls, center, radius, volume, reference):
        # Use the true planning area footprint, not only its bounding box.
        if volume.outline_circle is not None:
            outline = volume.outline_circle
            if outline.radius.units != "M":
                raise ValueError("Planning area circle radius must use meters")
            source = s2sphere.LatLng.from_degrees(
                outline.center.lat, outline.center.lng
            ).to_point()
            return (
                source.angle(center) * cls._EARTH_RADIUS_M + radius + 1.0
                < outline.radius.value
            )
        if volume.outline_polygon is None:
            raise ValueError("Planning area needs a polygon or circle footprint")
        polygon = Polygon(
            flatten(reference, vertex.as_s2sphere())
            for vertex in volume.outline_polygon.vertices
        )
        if not polygon.is_valid or polygon.is_empty:
            raise ValueError("Planning area polygon is invalid")
        center_xy = flatten(reference, s2sphere.LatLng.from_point(center))
        # Erosion checks the entire circular footprint at concave corners.
        return polygon.buffer(-(radius + 1.0)).covers(Point(*center_xy))

    @classmethod
    def _altitudes(cls, volume):
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
            low, high = cls._DEFAULT_ALTITUDES_M
        elif low is None:
            low = high - (cls._DEFAULT_ALTITUDES_M[1] - cls._DEFAULT_ALTITUDES_M[0])
        elif high is None:
            high = low + (cls._DEFAULT_ALTITUDES_M[1] - cls._DEFAULT_ALTITUDES_M[0])
        if high <= low:
            raise TestAreaNotApplicable(
                "Planning Area must have a positive altitude range"
            )
        return low + (high - low) * 0.25, high - (high - low) * 0.25

    def _circles(self):
        bounds = self._planning_area.get_extents()
        volume = self._planning_area.resolved_volume4d_with_times(None, None).volume
        reference = s2sphere.LatLng.from_degrees(
            (bounds.lat_min + bounds.lat_max) / 2,
            (bounds.lng_min + bounds.lng_max) / 2,
        )
        fallback = None
        for cid in self._candidate_cells(bounds):
            cell = s2sphere.Cell(cid)
            neighbors = set(cid.get_edge_neighbors())
            for edge in range(4):
                a, b = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
                inward = a.cross_prod(b).normalize()
                if inward.dot_prod(cell.get_center()) < 0:
                    inward = -inward
                radius = self._OIR_RADIUS_M
                # Project the planning-area center onto the actual S2 edge.
                # This avoids arbitrary fractions along an edge.
                direction = reference.to_point()
                boundary = (direction - inward * inward.dot_prod(direction)).normalize()
                if abs(a.angle(boundary) + boundary.angle(b) - a.angle(b)) > 1e-7:
                    boundary = self._interpolate_edge(a, b, 0.5)
                # The legacy inscribed loop must stay on the near side.
                # Derive the necessary center offset from the actual edge plane.
                projection = min(
                    inward.dot_prod(v) for v in self._legacy_vertices(boundary, radius)
                )
                distance = max(0.0, -projection * self._EARTH_RADIUS_M) + 0.01
                primary = self._move_point(boundary, inward, distance)
                query = self._move_point(boundary, -inward, 1.01)
                if distance + 0.01 >= radius:
                    continue
                query_cell = self._cell_id(query)
                if self._cell_id(primary) != cid or query_cell not in neighbors:
                    continue
                if any(
                    self._cell_id(p) != query_cell
                    for p in self._ring_points(query, self._QUERY_RADIUS_M)
                ):
                    continue
                if not self._circle_inside_volume(
                    primary, radius, volume, reference
                ) or not self._circle_inside_volume(
                    query, self._QUERY_RADIUS_M, volume, reference
                ):
                    continue
                plat, plng = self._point_to_lat_lng(primary)
                qlat, qlng = self._point_to_lat_lng(query)
                circles = (
                    Circle.from_meters(plat, plng, radius),
                    Circle.from_meters(qlat, qlng, self._QUERY_RADIUS_M),
                    Circle.from_meters(plat, plng, 50.0),
                )
                if all(
                    cell.contains(v) for v in self._legacy_vertices(primary, radius)
                ):
                    self._adversarial = True
                    return circles
                if fallback is None:
                    fallback = circles
        if fallback is not None:
            self._adversarial = False
            return fallback
        # Small or narrow areas may not contain a level-13 cell edge.
        # Still exercise the ASTM requirement with an ordinary overlapping pair.
        width_m = (
            (bounds.lng_max - bounds.lng_min)
            * self._EARTH_RADIUS_M
            * cos(reference.lat().radians)
            * pi
            / 180
        )
        height_m = (bounds.lat_max - bounds.lat_min) * self._EARTH_RADIUS_M * pi / 180
        radius = min(50.0, width_m / 5, height_m / 5)
        if radius > 2.0:
            for a in self._AREA_SAMPLE_FRACTIONS:
                for b in self._AREA_SAMPLE_FRACTIONS:
                    center = s2sphere.LatLng.from_degrees(
                        bounds.lat_min + (bounds.lat_max - bounds.lat_min) * a,
                        bounds.lng_min + (bounds.lng_max - bounds.lng_min) * b,
                    ).to_point()
                    query = self._move_point(center, s2sphere.ortho(center), radius)
                    if not self._circle_inside_volume(
                        center, radius, volume, reference
                    ) or not self._circle_inside_volume(
                        query, self._QUERY_RADIUS_M, volume, reference
                    ):
                        continue
                    lat, lng = self._point_to_lat_lng(center)
                    qlat, qlng = self._point_to_lat_lng(query)
                    self._adversarial = False
                    return (
                        Circle.from_meters(lat, lng, radius),
                        Circle.from_meters(qlat, qlng, self._QUERY_RADIUS_M),
                        Circle.from_meters(lat, lng, radius / 2),
                    )
        raise TestAreaNotApplicable(
            f"Cannot construct valid S2 boundary fixture in Planning Area: {bounds}"
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
        volume = self._planning_area.resolved_volume4d_with_times(None, None).volume
        try:
            alt0, alt1 = self._altitudes(volume)
            primary, boundary, inside = self._circles()
        except (TestAreaNotApplicable, NotImplementedError) as e:
            self.record_note("test_inapplicable", str(e))
            self.end_test_scenario()
            return

        self.record_note("fixture_constructed", "Valid overlapping circles constructed")
        self.record_note(
            "fixture_type", "adversarial" if self._adversarial else "general_overlap"
        )
        self.begin_test_case("Setup")
        self._cleanup_known_oir("Clear previous test OIR")
        self.end_test_case()
        self.begin_test_case("Discover an OIR through an overlapping circle")
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=60)
        self.begin_test_step("Create large circular OIR")
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
        self._check_step(
            "Boundary overlap is discoverable", boundary, start, end, alt0, alt1
        )
        self._check_step(
            "Ordinary contained circle is discoverable", inside, start, end, alt0, alt1
        )
        self.begin_test_step("Delete large circular OIR")
        oir_fragments.delete_oir_query(
            scenario=self, dss=self._dss, oir_id=self._oir_id, ovn=self._created_oir.ovn
        )
        self._created_oir = None
        self.end_test_step()
        self.end_test_case()
        self.end_test_scenario()

    def _check_step(self, title, circle, t0, t1, alt0, alt1):
        self.begin_test_step(title)
        self._search(title, circle, t0, t1, alt0, alt1)
        self.end_test_step()

    def _search(self, title, circle, t0, t1, alt0, alt1):
        query = Volume4D.from_values(
            t0=t0, t1=t1, alt0=alt0, alt1=alt1, circle=circle
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
                            f"query_time=[{t0}, {t1}]; query_altitude_m=[{alt0}, {alt1}]"
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

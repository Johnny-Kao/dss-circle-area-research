"""Research candidate: ASTM contract assertion with a certified S2-edge fixture.

The 20-vertex reference is used ONLY to certify diagnostic fixture selection,
not as the expected DSS result or a permitted implementation requirement.
"""

import s2sphere

from monitoring.monitorlib.geo import Circle
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap_review import (
    OIRCircleOverlap as BaseScenario,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap_review import (
    TestAreaNotApplicable,
)


class OIRCircleOverlap(BaseScenario):
    """DSS must discover an OIR whenever its true circular footprint overlaps."""

    _QUERY_RADIUS_M = 1.0
    _PRIMARY_RADII_M = (200.0, 150.0, 100.0)

    def _circles(self):
        bounds = self._planning_area.get_extents()
        volume = self._planning_area.resolved_volume4d_with_times(None, None).volume
        reference = s2sphere.LatLng.from_degrees(
            (bounds.lat_min + bounds.lat_max) / 2,
            (bounds.lng_min + bounds.lng_max) / 2,
        )
        direction = reference.to_point()
        for cid in self._candidate_cells(bounds):
            cell = s2sphere.Cell(cid)
            neighbors = set(cid.get_edge_neighbors())
            for edge in range(4):
                a, b = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
                inward = a.cross_prod(b).normalize()
                if inward.dot_prod(cell.get_center()) < 0:
                    inward = -inward
                boundary = (direction - inward * inward.dot_prod(direction)).normalize()
                if abs(a.angle(boundary) + boundary.angle(b) - a.angle(b)) > 1e-7:
                    boundary = self._interpolate_edge(a, b, 0.5)
                for radius in self._PRIMARY_RADII_M:
                    # Diagnostic fixture certification only. The expected API
                    # answer depends exclusively on the TRUE circle overlap.
                    projection = min(
                        inward.dot_prod(v)
                        for v in self._legacy_vertices(boundary, radius)
                    )
                    x = max(0.0, -projection * self._EARTH_RADIUS_M) + 0.01
                    y = self._QUERY_RADIUS_M + 0.01
                    if x + y >= radius + self._QUERY_RADIUS_M - 0.01:
                        continue
                    primary = self._move_point(boundary, inward, x)
                    query = self._move_point(boundary, -inward, y)
                    query_cell = self._cell_id(query)
                    if self._cell_id(primary) != cid or query_cell not in neighbors:
                        continue
                    if any(
                        self._cell_id(p) != query_cell
                        for p in self._ring_points(query, self._QUERY_RADIUS_M)
                    ):
                        continue
                    if not all(
                        cell.contains(v) for v in self._legacy_vertices(primary, radius)
                    ):
                        continue
                    if not self._circle_inside_volume(
                        primary, radius, volume, reference
                    ) or not self._circle_inside_volume(
                        query, self._QUERY_RADIUS_M, volume, reference
                    ):
                        continue
                    overlap = (
                        radius
                        + self._QUERY_RADIUS_M
                        - primary.angle(query) * self._EARTH_RADIUS_M
                    )
                    if overlap <= 0.01:
                        continue
                    plat, plng = self._point_to_lat_lng(primary)
                    qlat, qlng = self._point_to_lat_lng(query)
                    self._adversarial = True
                    self._fixture_detail = {
                        "diagnostic": True,
                        "primary_radius_m": radius,
                        "query_radius_m": self._QUERY_RADIUS_M,
                        "true_overlap_m": overlap,
                        "cell_id": cid.id(),
                    }
                    return (
                        Circle.from_meters(plat, plng, radius),
                        Circle.from_meters(qlat, qlng, self._QUERY_RADIUS_M),
                        Circle.from_meters(plat, plng, min(50.0, radius / 2)),
                    )
        raise TestAreaNotApplicable(
            f"No diagnostic S2 boundary fixture within Planning Area: {bounds}"
        )

"""Research-only contract-first circular OIR search fixture.

The expected result is defined by true circle overlap, not old S2 polygon behavior.
S2 is used only to choose a challenging location for the fixture.
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
    _QUERY_RADIUS_M = 1.0
    _OVERLAP_M = 0.5
    _QUERY_CLEARANCE_M = 0.1
    _PRIMARY_RADII_M = (200.0, 150.0, 100.0, 50.0)

    def _circles(self):
        bounds = self._planning_area.get_extents()
        volume = self._planning_area.resolved_volume4d_with_times(None, None).volume
        reference = s2sphere.LatLng.from_degrees(
            (bounds.lat_min + bounds.lat_max) / 2,
            (bounds.lng_min + bounds.lng_max) / 2,
        )
        reference_point = reference.to_point()
        query_offset = self._QUERY_RADIUS_M + self._QUERY_CLEARANCE_M

        for cid in self._candidate_cells(bounds):
            cell = s2sphere.Cell(cid)
            neighbor_ids = set(cid.get_edge_neighbors())
            for edge in range(4):
                a, b = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
                inward = a.cross_prod(b).normalize()
                if inward.dot_prod(cell.get_center()) < 0:
                    inward = -inward
                boundary = (
                    reference_point - inward * inward.dot_prod(reference_point)
                ).normalize()
                if abs(a.angle(boundary) + boundary.angle(b) - a.angle(b)) > 1e-7:
                    boundary = self._interpolate_edge(a, b, 0.5)
                query = self._move_point(boundary, -inward, query_offset)
                if self._cell_id(query) not in neighbor_ids:
                    continue
                if any(
                    self._cell_id(p) != self._cell_id(query)
                    for p in self._ring_points(query, self._QUERY_RADIUS_M)
                ):
                    continue
                if not self._circle_inside_volume(
                    query, self._QUERY_RADIUS_M, volume, reference
                ):
                    continue
                for radius in self._PRIMARY_RADII_M:
                    # d = R + r - overlap; the two centers straddle the cell edge.
                    primary_offset = (
                        radius + self._QUERY_RADIUS_M - self._OVERLAP_M - query_offset
                    )
                    primary = self._move_point(boundary, inward, primary_offset)
                    if self._cell_id(primary) != cid:
                        continue
                    if not self._circle_inside_volume(
                        primary, radius, volume, reference
                    ):
                        continue
                    separation = primary.angle(query) * self._EARTH_RADIUS_M
                    actual_overlap = radius + self._QUERY_RADIUS_M - separation
                    if abs(actual_overlap - self._OVERLAP_M) > 0.001:
                        continue
                    plat, plng = self._point_to_lat_lng(primary)
                    qlat, qlng = self._point_to_lat_lng(query)
                    # This is a cross-cell ASTM fixture, not a certified old-bug reproducer.
                    self._adversarial = False
                    self._fixture_detail = {
                        "crosses_s2_edge": True,
                        "radius_m": radius,
                        "query_radius_m": self._QUERY_RADIUS_M,
                        "overlap_m": actual_overlap,
                        "cell_id": cid.id(),
                    }
                    return (
                        Circle.from_meters(plat, plng, radius),
                        Circle.from_meters(qlat, qlng, self._QUERY_RADIUS_M),
                        Circle.from_meters(plat, plng, min(radius / 2, 50)),
                    )
        raise TestAreaNotApplicable(
            f"No legal cross-cell circular overlap fixture in Planning Area: {bounds}"
        )

"""Inspect which gate rejects adversarial S2 geometries (research only).

Run alongside the user-supplied pr1911_review_revision.zip's test_geometry.py.
No DSS mutations; geometry emulator only.
"""
from collections import Counter
from test_geometry import (
    CONFIGS, FRACTIONS, QR, EARTH, SAMPLES, cid, llp, verts, center,
    interp, move, ring, loop, contains, circ_in,
)

def inspect(bounds, configs=CONFIGS, fractions=FRACTIONS, samples=SAMPLES):
    lat0, lat1, lng0, lng1 = bounds
    cells = {
        cid(llp(lat0 + (lat1-lat0)*af, lng0 + (lng1-lng0)*bf))
        for af in samples for bf in samples
    }
    counts = Counter(cells=len(cells))
    for c in sorted(cells):
        vs, cc = verts(c), center(c)
        f, i, j = c
        neighbors = {(f,i-1,j),(f,i+1,j),(f,i,j-1),(f,i,j+1)}
        for e in range(4):
            start, end = vs[e], vs[(e+1)%4]
            normal = start.cross(end).unit()
            if normal.dot(cc) < 0:
                normal = -normal
            for radius, crossing, query_offset in configs:
                for fraction in fractions:
                    counts["proposed"] += 1
                    boundary = interp(start, end, fraction)
                    primary = move(boundary, normal, radius-crossing)
                    query = move(boundary, -normal, query_offset)
                    if cid(primary) != c:
                        counts["primary_out"] += 1; continue
                    qcell = cid(query)
                    if qcell not in neighbors:
                        counts["neighbor_out"] += 1; continue
                    if any(cid(p) != qcell for p in ring(query, QR)):
                        counts["query_out"] += 1; continue
                    if any(not contains(c, p) for p in loop(primary, radius, 20)):
                        counts["legacy_polygon_crosses_boundary"] += 1; continue
                    if primary.angle(query)*EARTH >= radius+QR:
                        counts["no_real_overlap"] += 1; continue
                    if not circ_in(primary, radius, bounds):
                        counts["primary_outside_planning_area"] += 1; continue
                    if not circ_in(query, QR, bounds):
                        counts["query_outside_planning_area"] += 1; continue
                    counts["success"] += 1
                    return counts
    return counts

if __name__ == "__main__":
    for name, area in (
        ("failed_south", (-60., -59.94, 0., 0.06)),
        ("failed_equator", (0., 0.06, -60., -59.94)),
        ("passed_tokyo", (35.65,35.71,139.73,139.79)),
    ):
        print(name, dict(inspect(area, fractions=(0.5,))))

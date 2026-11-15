"""Generate semantic-valid S2 boundary fixtures without using any legacy algorithm.

Output JSONL to stdout for a separate version-differential oracle. The generator
knows only true-circle overlap, S2 geography, and a user-supplied area.
"""

import json
from math import cos, pi, radians, sin

import s2sphere as s

EARTH_M = 6371010.0
LEVEL = 13


def move(origin, tangent, meters):
    a = meters / EARTH_M
    return (origin * cos(a) + tangent * sin(a)).normalize()


def ring(center, radius, n=32):
    y = s.ortho(center)
    x = y.cross_prod(center).normalize()
    angle = radius / EARTH_M
    return [
        (
            center * cos(angle)
            + x * (sin(angle) * cos(2 * pi * k / n))
            + y * (sin(angle) * sin(2 * pi * k / n))
        ).normalize()
        for k in range(n)
    ]


def ll(p):
    v = s.LatLng.from_point(p)
    return [v.lat().degrees, v.lng().degrees]


def cid(p):
    return s.CellId.from_lat_lng(s.LatLng.from_point(p)).parent(LEVEL)


def edgepoint(a, b, f):
    ang = a.angle(b)
    return (
        a * (sin((1 - f) * ang) / sin(ang)) + b * (sin(f * ang) / sin(ang))
    ).normalize()


def area_bounds(lat, lng, width=3000, height=3000):
    dy = height / 2 / 111195
    dx = width / 2 / (111195 * max(0.02, cos(radians(lat))))
    return lat - dy, lat + dy, lng - dx, lng + dx


def inside_box(p, radius, bounds):
    a, b, c, d = bounds
    return all(a < lat < b and c < lng < d for lat, lng in map(ll, ring(p, radius)))


def candidates(name, lat, lng, max_results=160):
    bounds = area_bounds(lat, lng)
    ref = s.LatLng.from_degrees(lat, lng).to_point()
    cell_ids = {}
    for a in range(1, 8):
        for b in range(1, 8):
            pt = s.LatLng.from_degrees(
                bounds[0] + (bounds[1] - bounds[0]) * a / 8,
                bounds[2] + (bounds[3] - bounds[2]) * b / 8,
            ).to_point()
            c = cid(pt)
            cell_ids[c.id()] = c
    # Cover diverse cells and edge orientations BEFORE varying radii/overlap.
    # Otherwise an early max_results limit samples only the lowest-numbered cell.
    edges = []
    for cell_id in sorted(cell_ids.values(), key=lambda c: c.id()):
        cell = s.Cell(cell_id)
        neighbors = set(cell_id.get_edge_neighbors())
        for edge in range(4):
            v0, v1 = cell.get_vertex(edge), cell.get_vertex((edge + 1) % 4)
            inward = v0.cross_prod(v1).normalize()
            if inward.dot_prod(cell.get_center()) < 0:
                inward = -inward
            projected = (ref - inward * inward.dot_prod(ref)).normalize()
            positions = (
                [projected]
                if abs(v0.angle(projected) + projected.angle(v1) - v0.angle(v1)) < 1e-7
                else []
            )
            positions += [edgepoint(v0, v1, f) for f in (0.5, 0.25, 0.75)]
            for bp in positions:
                edges.append((cell_id, neighbors, edge, inward, bp))
    count = 0
    configurations = [
        (r, d) for r in (200, 150, 100, 80, 250, 300, 400) for d in (0.5, 0.1, 0.05)
    ]
    # Round-robin across BOTH edge locations and radii, including short scans.
    for phase in range(len(configurations)):
        for idx, (cell_id, neighbors, edge, inward, bp) in enumerate(edges):
            radius, overlap = configurations[(phase + idx) % len(configurations)]
            query_r = 1.0
            query_offset = query_r + 0.01
            primary_offset = radius + query_r - overlap - query_offset
            if primary_offset <= 0:
                continue
            a = move(bp, inward, primary_offset)
            b = move(bp, -inward, query_offset)
            qb = cid(b)
            if cid(a) != cell_id or qb not in neighbors:
                continue
            if any(cid(p) != qb for p in ring(b, query_r)):
                continue
            if not inside_box(a, radius, bounds) or not inside_box(b, query_r, bounds):
                continue
            depth = radius + query_r - a.angle(b) * EARTH_M
            if abs(depth - overlap) > 0.001:
                continue
            yield {
                "name": name,
                "radius": radius,
                "primary": ll(a),
                "query": ll(b),
                "overlap": depth,
                "primaryCell": cell_id.id(),
                "queryCell": qb.id(),
                "edge": edge,
                "caseIndex": count,
            }
            count += 1
            if count >= max_results:
                return


def corner_candidates(name, lat, lng, max_results=160):
    """True circular overlap across diagonal S2 cells near a cell vertex."""
    bounds = area_bounds(lat, lng)
    cell_ids = {}
    for i in range(1, 8):
        for j in range(1, 8):
            pt = s.LatLng.from_degrees(
                bounds[0] + (bounds[1] - bounds[0]) * i / 8,
                bounds[2] + (bounds[3] - bounds[2]) * j / 8,
            ).to_point()
            ci = cid(pt)
            cell_ids[ci.id()] = ci
    corners = []
    for cell_id in sorted(cell_ids.values(), key=lambda v: v.id()):
        cell = s.Cell(cell_id)
        neighbors = set(cell_id.get_edge_neighbors())
        for vertex in range(4):
            v = cell.get_vertex(vertex)
            center = cell.get_center()
            inward = (center - v * center.dot_prod(v)).normalize()
            corners.append((cell_id, neighbors, v, inward, vertex))
    configs = [
        (r, d) for r in (200, 150, 100, 80, 250, 300, 400) for d in (0.5, 0.1, 0.05)
    ]
    count = 0
    for phase in range(len(configs)):
        for idx, (cell_id, neighbors, vertex_pt, inward, vertex) in enumerate(corners):
            radius, overlap = configs[(phase + idx) % len(configs)]
            query_radius = 1.0
            query_offset = 2.0
            primary_offset = radius + query_radius - overlap - query_offset
            if primary_offset <= 0:
                continue
            a = move(vertex_pt, inward, primary_offset)
            b = move(vertex_pt, -inward, query_offset)
            bc = cid(b)
            if cid(a) != cell_id or bc == cell_id or bc in neighbors:
                continue
            if any(cid(p) != bc for p in ring(b, query_radius)):
                continue
            if not inside_box(a, radius, bounds) or not inside_box(
                b, query_radius, bounds
            ):
                continue
            depth = radius + query_radius - a.angle(b) * EARTH_M
            if abs(depth - overlap) > 0.001:
                continue
            yield {
                "name": name,
                "radius": radius,
                "primary": ll(a),
                "query": ll(b),
                "overlap": depth,
                "primaryCell": cell_id.id(),
                "queryCell": bc.id(),
                "vertex": vertex,
                "mode": "corner",
                "caseIndex": count,
            }
            count += 1
            if count >= max_results:
                return


PLACES = [
    ("Kentland", 37.20005, -80.579),
    ("Stanford", 37.43, -122.17),
    ("Tokyo", 35.68, 139.75),
    ("Zurich", 47.38, 8.54),
    ("Helsinki", 60.17, 24.94),
    ("Equator", 0.5, 23.5),
    ("Sydney", -33.9, 151.2),
    ("Tierra", -55, -68),
    ("Norway", 72, 20),
    ("Arctic", 81, -5),
    ("Antarctica", -75, 110),
]
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--max-per-area", type=int, default=160)
    p.add_argument("--mode", choices=("edge", "corner", "both"), default="both")
    args = p.parse_args()
    for name, lat, lng in PLACES:
        generators = []
        if args.mode in ("edge", "both"):
            generators.append(candidates(name, lat, lng, args.max_per_area))
        if args.mode in ("corner", "both"):
            generators.append(corner_candidates(name, lat, lng, args.max_per_area))
        for group in generators:
            for entry in group:
                print(json.dumps(entry, sort_keys=True))

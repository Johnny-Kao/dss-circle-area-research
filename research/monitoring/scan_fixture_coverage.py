"""Research-only scan of how often the real scenario can construct a valid fixture.

This is NOT a pass/fail certification of DSS. It tests the current generator.
"""
from math import cos, radians
from types import SimpleNamespace

from monitoring.monitorlib.geo import Circle, LatLngBoundingBox, LatLngPoint, Polygon, Volume3D
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    OIRCircleOverlap,
    TestAreaNotApplicable,
)


def area_at(lat, lng, shape):
    if shape == "circle":
        volume = Volume3D(outline_circle=Circle.from_meters(lat, lng, 1500))
        width_m = height_m = 3000
    else:
        height_m = {"rectangle": 3000, "concave_l": 3000,
                    "tiny": 100, "corridor": 3000}[shape]
        width_m = {"rectangle": 3000, "concave_l": 3000,
                   "tiny": 100, "corridor": 50}[shape]
        dy = height_m / 2 / 111195
        dx = width_m / 2 / (111195 * max(0.02, cos(radians(lat))))
        south, north = lat - dy, lat + dy
        west, east = lng - dx, lng + dx
        midlat = south + (north - south) * 0.55
        midlng = west + (east - west) * 0.55
        if shape == "concave_l":
            coords = [(south, west), (south, east), (midlat, east),
                      (midlat, midlng), (north, midlng), (north, west)]
        else:
            coords = [(south, west), (south, east), (north, east), (north, west)]
        volume = Volume3D(outline_polygon=Polygon(vertices=[
            LatLngPoint(lat=y, lng=x) for y, x in coords
        ]))
    dy = height_m / 2 / 111195
    dx = width_m / 2 / (111195 * max(0.02, cos(radians(lat))))
    bounds = LatLngBoundingBox(lat_min=lat-dy, lat_max=lat+dy,
                               lng_min=lng-dx, lng_max=lng+dx)
    return SimpleNamespace(
        get_extents=lambda: bounds,
        resolved_volume4d_with_times=lambda start, end: SimpleNamespace(volume=volume),
    )


places = [(37.2, -80.58), (35.68, 139.75), (47.38, 8.54),
          (60.17, 24.94), (37.43, -122.17),
          (0.5, 23.5), (-33.9, 151.2), (-55, -68),
          (72, 20), (81.0, -5), (-75, 110)]
shapes = ("rectangle", "concave_l", "circle", "tiny", "corridor")
results = {s: [0, 0] for s in shapes}
for lat, lng in places:
    for shape in shapes:
        scenario = object.__new__(OIRCircleOverlap)
        scenario._planning_area = area_at(lat, lng, shape)
        try:
            scenario._circles()
            results[shape][0] += 1
        except TestAreaNotApplicable as exc:
            results[shape][1] += 1
            print(f"UNSUPPORTED lat={lat:6.2f} lng={lng:8.2f} shape={shape}: {exc}")

for shape, (ok, missing) in results.items():
    print(f"{shape:12s} fixture_created={ok}/{ok+missing} not_applicable={missing}")

# This experiment is observational: do not equate unsuitable areas with DSS defects.

print("EXPERIMENTS: rectangle in 11 geographic positions")
original_configs = OIRCircleOverlap._CIRCLE_CONFIGURATIONS
original_edges = OIRCircleOverlap._EDGE_FRACTIONS
experiments = {
    "baseline": (original_configs, original_edges),
    "more_edge_positions": (original_configs, tuple(i / 20 for i in range(1, 20))),
    "more_radii": (
        tuple((radius, crossing, 1.15) for radius in (50, 80, 100, 120, 150, 200, 250, 300)
              for crossing in (0.5, 0.85)),
        original_edges,
    ),
    "more_radii_and_edges": (
        tuple((radius, crossing, 1.15) for radius in (50, 80, 100, 120, 150, 200, 250, 300)
              for crossing in (0.5, 0.85)),
        tuple(i / 20 for i in range(1, 20)),
    ),
}
for label, (configs, edges) in experiments.items():
    OIRCircleOverlap._CIRCLE_CONFIGURATIONS = configs
    OIRCircleOverlap._EDGE_FRACTIONS = edges
    passed, failed = [], []
    for lat, lng in places:
        scenario = object.__new__(OIRCircleOverlap)
        scenario._planning_area = area_at(lat, lng, "rectangle")
        try:
            scenario._circles()
            passed.append((lat, lng))
        except TestAreaNotApplicable:
            failed.append((lat, lng))
    print(f"{label}: success={len(passed)}/11 failed={failed}")
OIRCircleOverlap._CIRCLE_CONFIGURATIONS = original_configs
OIRCircleOverlap._EDGE_FRACTIONS = original_edges

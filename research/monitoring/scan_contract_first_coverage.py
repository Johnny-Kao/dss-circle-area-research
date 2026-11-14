"""Research-only matrix for contract-first circular OIR boundary fixture."""

from math import cos, radians
from types import SimpleNamespace

from monitoring.monitorlib.geo import (
    Circle,
    LatLngBoundingBox,
    LatLngPoint,
    Polygon,
    Volume3D,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    OIRCircleOverlap,
    TestAreaNotApplicable,
)

PLACES = [
    ("Kentland", 37.2, -80.58),
    ("Tokyo", 35.68, 139.75),
    ("Zurich", 47.38, 8.54),
    ("Helsinki", 60.17, 24.94),
    ("Stanford", 37.43, -122.17),
    ("Equator", 0.5, 23.5),
    ("Sydney", -33.9, 151.2),
    ("Tierra", -55, -68),
    ("Norway", 72, 20),
    ("Arctic", 81, -5),
    ("Antarctic", -75, 110),
]
SHAPES = ("rectangle", "concave_l", "circle", "tiny", "corridor")


def area_at(lat, lng, shape):
    width = 50 if shape == "corridor" else 100 if shape == "tiny" else 3000
    height = 100 if shape == "tiny" else 3000
    dy = height / 2 / 111195
    dx = width / 2 / (111195 * max(0.02, cos(radians(lat))))
    south, north, west, east = lat - dy, lat + dy, lng - dx, lng + dx
    if shape == "circle":
        volume = Volume3D(outline_circle=Circle.from_meters(lat, lng, 1500))
    else:
        midlat = south + (north - south) * 0.55
        midlng = west + (east - west) * 0.55
        if shape == "concave_l":
            coords = [
                (south, west),
                (south, east),
                (midlat, east),
                (midlat, midlng),
                (north, midlng),
                (north, west),
            ]
        else:
            coords = [(south, west), (south, east), (north, east), (north, west)]
        volume = Volume3D(
            outline_polygon=Polygon(
                vertices=[LatLngPoint(lat=y, lng=x) for y, x in coords]
            )
        )
    bounds = LatLngBoundingBox(lat_min=south, lat_max=north, lng_min=west, lng_max=east)
    return SimpleNamespace(
        get_extents=lambda: bounds,
        resolved_volume4d_with_times=lambda start, end: SimpleNamespace(volume=volume),
    )


def main():
    totals = {s: [0, 0] for s in SHAPES}
    for place, lat, lng in PLACES:
        for shape in SHAPES:
            scenario = object.__new__(OIRCircleOverlap)
            scenario._planning_area = area_at(lat, lng, shape)
            try:
                scenario._circles()
                assert scenario._fixture_detail["diagnostic"]
                assert scenario._fixture_detail["true_overlap_m"] > 0.01
                totals[shape][0] += 1
                print(
                    f"OK {place:10} {shape:10} R={scenario._fixture_detail['primary_radius_m']:g}m"
                )
            except TestAreaNotApplicable:
                totals[shape][1] += 1
                print(f"NA {place:10} {shape:10}")
    for shape, (success, na) in totals.items():
        print(f"SUMMARY {shape}: {success}/11; not_applicable={na}")
    return totals


if __name__ == "__main__":
    main()

"""Research-only coverage of a real, geographically constructed DSS search fixture."""

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


places = [
    (37.2, -80.58),
    (35.68, 139.75),
    (47.38, 8.54),
    (60.17, 24.94),
    (37.43, -122.17),
    (0.5, 23.5),
    (-33.9, 151.2),
    (-55, -68),
    (72, 20),
    (81, -5),
    (-75, 110),
]
shapes = ("rectangle", "concave_l", "circle", "tiny", "corridor")
results = {s: [0, 0, 0] for s in shapes}
for lat, lng in places:
    for shape in shapes:
        scenario = object.__new__(OIRCircleOverlap)
        scenario._planning_area = area_at(lat, lng, shape)
        try:
            scenario._circles()
            results[shape][0] += 1
            results[shape][2] += int(scenario._adversarial)
        except TestAreaNotApplicable:
            results[shape][1] += 1

for shape, (ok, missing, adversarial) in results.items():
    print(
        f"{shape}: fixture={ok}/{ok + missing}, adversarial={adversarial}, "
        f"general_overlap={ok - adversarial}, unavailable={missing}"
    )

"""Public research: actual Monitoring PlanningArea volume geometry, not a polygon proxy."""
from __future__ import annotations

import os
from time import perf_counter
from types import SimpleNamespace
from implicitdict import ImplicitDict

from monitoring.monitorlib.geo import Circle, Polygon, Volume3D
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    FixtureUnavailable, OIRCircleOverlap,
)

class TestArea:
    def __init__(self, volume):
        self.volume = volume
    def get_extents(self):
        from monitoring.monitorlib.geo import make_latlng_rect
        r = make_latlng_rect(self.volume)
        return SimpleNamespace(
            lat_min=r.lat_lo().degrees, lat_max=r.lat_hi().degrees,
            lng_min=r.lng_lo().degrees, lng_max=r.lng_hi().degrees,
        )

def vertices(lat, lon, xy):
    # Local planar meter offsets are appropriate for these small, mid-latitude shapes.
    from math import cos, radians
    return [(lat+y/111195.0, lon+x/(111195.0*cos(radians(lat)))) for x,y in xy]

def shape(lat,lon,kind,scale):
    if kind=="circle":
        return ImplicitDict.parse(Volume4D.from_values(circle=Circle.from_meters(lat,lon,scale)).volume, Volume3D)
    if kind=="square":
        xy=[(-scale,-scale),(scale,-scale),(scale,scale),(-scale,scale)]
    elif kind=="long":
        xy=[(-3*scale,-scale/3),(3*scale,-scale/3),(3*scale,scale/3),(-3*scale,scale/3)]
    elif kind=="triangle":
        xy=[(-scale,-scale),(scale,-scale),(0,scale)]
    elif kind=="L":
        xy=[(-scale,-scale),(scale,-scale),(scale,-scale/3),(-scale/3,-scale/3),(-scale/3,scale),(-scale,scale)]
    elif kind=="concave":
        xy=[(-scale,-scale),(scale,-scale),(scale,scale),(-scale/3,scale),(-scale/3,0),(-scale,0)]
    else:
        raise ValueError(kind)
    return ImplicitDict.parse(Volume4D.from_values(polygon=Polygon.from_coords(vertices(lat,lon,xy))).volume, Volume3D)

def main():
    kinds=["circle","square","long","triangle","L","concave"]
    # representative geography includes latitude spread and opposite hemispheres
    sites=[(37.20,-80.58),(47.37,8.54),(35.68,139.69),(-33.87,151.21),
           (0.0,0.0),(60.17,24.94),(-22.90,-43.20),(52.37,4.90)]
    print("SCENARIO_SOURCE=actual Monitoring _fixtures / _fits")
    times=[]
    for kind in kinds:
        for scale in [500,750,1000,1500,2500,5000]:
            full=0;unavailable=0;other=0
            details=[]
            for lat,lon in sites:
                volume=shape(lat,lon,kind,scale)
                scenario=object.__new__(OIRCircleOverlap)
                scenario._planning_area=TestArea(volume)
                # Call exact production-like fixture construction; only record_note is mocked.
                scenario.record_note=lambda *args,**kwargs: None
                try:
                    started=perf_counter()
                    try:
                        fixtures=scenario._fixtures(volume)
                    finally:
                        times.append(perf_counter()-started)
                    if len(fixtures)!=4:raise AssertionError(f"Unexpected fixture count {len(fixtures)}")
                    full+=1
                except FixtureUnavailable as e:
                    unavailable+=1
                    if len(details)<2:details.append(str(e)[:120])
                except Exception as e:
                    other+=1
                    details.append(f"{type(e).__name__}: {e}")
            print(f"REAL_PLANNING shape={kind} scale_m={scale} full={full}/8 unavailable={unavailable} errors={other} examples={details}",flush=True)
            if other:raise AssertionError(f"Unexpected error with {kind},scale={scale}")
    times.sort()
    if times:
        print(f"COST variant={os.getenv('VARIANT','unknown')} calls={len(times)} total_s={sum(times):.6f} median_ms={times[len(times)//2]*1000:.3f} p95_ms={times[min(len(times)-1,int(len(times)*.95))]*1000:.3f} max_ms={times[-1]*1000:.3f}",flush=True)
    # Edge geography must be exercised through Monitoring's exact shape handling.
    unusual=[(85.0,0.0),(89.9,0.0),(-89.9,0.0),
             (0.0,179.9),(0.0,-179.9),(45.0,179.9),(-45.0,-179.9),
             (35.2643897,45.0)]
    for kind in ["circle","square"]:
        for scale in [1500,5000]:
            ok=0;unavailable=0;errors=[]
            for lat,lon in unusual:
                try:
                    volume=shape(lat,lon,kind,scale)
                    scenario=object.__new__(OIRCircleOverlap)
                    scenario._planning_area=TestArea(volume)
                    scenario.record_note=lambda *args,**kwargs: None
                    cases=scenario._fixtures(volume)
                    if len(cases)!=4:raise AssertionError(len(cases))
                    ok+=1
                except FixtureUnavailable:
                    unavailable+=1
                except Exception as e:
                    errors.append(f"{lat},{lon}:{type(e).__name__}:{str(e)[:90]}")
            print(f"EDGE_PLANNING shape={kind} scale_m={scale} full={ok}/{len(unusual)} unavailable={unavailable} errors={errors}",flush=True)
if __name__=="__main__":main()

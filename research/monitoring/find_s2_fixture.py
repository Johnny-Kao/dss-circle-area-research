"""Research-only scan: locate real cap points in S2 level-13 cells not touching a 20-gon."""
import math
import s2sphere
from shapely.geometry import Polygon, Point

R = 6371010.0
def point_at(lat, lng, distance, bearing):
    p, l, a, t = map(math.radians, (lat, lng, 0, bearing))
    a = distance / R
    q = math.asin(math.sin(p)*math.cos(a)+math.cos(p)*math.sin(a)*math.cos(t))
    v = l + math.atan2(math.sin(t)*math.sin(a)*math.cos(p), math.cos(a)-math.sin(p)*math.sin(q))
    return math.degrees(q), math.degrees(v)

def scan(area_shift):
    center_lat=37.201 + (-10000/111195 if area_shift==2 else 0)
    center_lng=-80.576 + (10000/(111195*0.797) if area_shift==1 else 0)
    checked=0
    for dlat in [0, .002, -.002, .004, -.004, .006, -.006]:
      for dlng in [0, .003, -.003, .006, -.006, .009, -.009]:
       lat=center_lat+dlat; lng=center_lng+dlng
       kmx=111195*math.cos(math.radians(lat))
       for radius in [900,1100,1300]:
        def xy(p):
          return (p[1]*kmx,p[0]*111195)
        polygon=Polygon([xy(point_at(lat,lng,radius,b)) for b in range(0,360,18)])
        cache={}
        for fraction in [.995,.998,.999]:
         for bearing in range(0,360,2):
          qlat,qlng=point_at(lat,lng,radius*fraction,bearing)
          cellid=s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(qlat,qlng)).parent(13)
          key=cellid.id()
          if key not in cache:
             cell=s2sphere.Cell(cellid)
             corners=[s2sphere.LatLng.from_point(cell.get_vertex(i)) for i in range(4)]
             cellpolygon=Polygon([xy((c.lat().degrees,c.lng().degrees)) for c in corners])
             cache[key]=cellpolygon
          cellpolygon=cache[key]
          checked+=1
          if (not cellpolygon.intersects(polygon) and
              cellpolygon.boundary.distance(Point(xy((qlat,qlng))))>3):
            print(f"SHIFT={area_shift} center={lat:.10f},{lng:.10f} radius={radius} query={qlat:.10f},{qlng:.10f} bearing={bearing} fraction={fraction} checked={checked} cell={key}", flush=True)
            return
    print(f"SHIFT={area_shift} NO_CANDIDATE checked={checked}",flush=True)

if __name__=="__main__":
 for i in (0,1,2):
  scan(i)

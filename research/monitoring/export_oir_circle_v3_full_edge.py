"""Research-only exhaustive *real-circle* edge fixture discovery.

Unlike the old bug oracle, no historical polygon approximation is imported.
Scan more S2 cells/edge directions/boundary points, rather than just first usable
edge near the Planning Area midpoint.  Results are evaluated separately by Go.
"""
import json
from itertools import product
from math import pi

import s2sphere

from monitoring.monitorlib.geo import EARTH_RADIUS_M
from monitoring.uss_qualifier.scenarios.astm.utm.dss.oir_circle_overlap import (
    OIRCircleOverlap,
)
from test_oir_circle_v2 import planning_area

AREAS = (
    ("Kentland", 37.2, -80.58),
    ("Stanford", 37.43, -122.17),
    ("Tokyo", 35.68, 139.75),
    ("Zurich", 47.38, 8.54),
    ("Helsinki", 60.17, 24.94),
)
SAMPLES = tuple(i/8 for i in range(1,8))
RADII = (100.0, 150.0, 200.0, 250.0, 300.0)
DEPTHS = (0.1, 0.5)
MAX_PER_REGION = 1200
QUERY_MARGIN = 0.01

for name, lat, lng in AREAS:
    resource, volume = planning_area(lat, lng)
    scenario = object.__new__(OIRCircleOverlap)
    scenario._planning_area = resource
    bounds=resource.get_extents()
    reference=scenario._reference(volume)
    center=reference.to_point()
    cells={}
    for fx,fy in product(SAMPLES,repeat=2):
        p=s2sphere.LatLng.from_degrees(
            bounds.lat_min+(bounds.lat_max-bounds.lat_min)*fx,
            bounds.lng_min+(bounds.lng_max-bounds.lng_min)*fy,
        ).to_point()
        cid=scenario._cell(p)
        cells[cid.id()]=cid
    emitted=0
    witness_preview=[]
    for cid in sorted(cells.values(),key=lambda x:x.id()):
        cell=s2sphere.Cell(cid)
        neighbors=set(cid.get_edge_neighbors())
        for edge in range(4):
            a,b=cell.get_vertex(edge),cell.get_vertex((edge+1)%4)
            inward=a.cross_prod(b).normalize()
            if inward.dot_prod(cell.get_center())<0:
                inward=-inward
            projected=(center-inward*inward.dot_prod(center)).normalize()
            # Use projection only if it lies on the actual edge segment.
            if abs(a.angle(projected)+projected.angle(b)-a.angle(b)) > 1e-7:
                projected=(a+b).normalize()
            positions=(
                projected,(a+b).normalize(),
                (a*3+b).normalize(),(a+b*3).normalize()
            )
            for which,position in enumerate(positions):
                q=scenario._move(position,-inward,scenario.QUERY_RADIUS_M+QUERY_MARGIN)
                qid=scenario._cell(q)
                if qid not in neighbors or not scenario._circle_in_cell(
                    s2sphere.Cell(qid),q,scenario.QUERY_RADIUS_M
                ):
                    continue
                if not scenario._fits(q,scenario.QUERY_RADIUS_M,volume,reference):
                    continue
                for radius,depth in product(RADII,DEPTHS):
                    primary_center=scenario._move(position,inward,radius-depth-QUERY_MARGIN)
                    if scenario._cell(primary_center)!=cid:
                        continue
                    if not scenario._fits(primary_center,radius,volume,reference):
                        continue
                    overlap=radius+scenario.QUERY_RADIUS_M-primary_center.angle(q)*EARTH_RADIUS_M
                    if abs(overlap-depth)>0.001:
                        continue
                    primary=scenario._circle(primary_center,radius)
                    query=scenario._circle(q,scenario.QUERY_RADIUS_M)
                    print(json.dumps({
                        'name':name,'caseIndex':emitted,'radius':radius,
                        'primary':[primary.center.lat,primary.center.lng],
                        'query':[query.center.lat,query.center.lng],
                        'cell':cid.id(),'neighbor':qid.id(),'edge':edge,
                        'which':which,'depth':depth,'overlap':overlap,
                    }))
                    emitted+=1
                    if emitted>=MAX_PER_REGION:break
                if emitted>=MAX_PER_REGION:break
            if emitted>=MAX_PER_REGION:break
        if emitted>=MAX_PER_REGION:break
    print(f"{name}: explored {emitted} valid true-circle fixtures",file=__import__('sys').stderr)

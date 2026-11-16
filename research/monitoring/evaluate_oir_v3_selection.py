"""Research-only evaluate fixed, geometry-only selection designs across area datasets.

We are not selecting based on historic DSS responses at runtime.  The separate
oracle measures how each proposed static rule behaves against old/fixed DSS.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

records=[json.loads(s) for s in Path(sys.argv[1]).read_text().splitlines()]
results=[json.loads(s) for s in Path(sys.argv[2]).read_text().splitlines()]
assert len(records)==len(results)
areas=defaultdict(list)
for a,b in zip(records,results):
    assert a['name']==b['name'] and a['caseIndex']==b['caseIndex']
    areas[a['name']].append((a,b))

def rule(edge,position=None,radius=None,depth=None):
    return (edge,position,radius,depth)

def select(area,choices):
    picked=[]
    for edge,position,radius,depth in choices:
        for a,b in area:
            if (a['edge']==edge
                and (position is None or a['which']==position)
                and (radius is None or a['radius']==radius)
                and (depth is None or a['depth']==depth)
                and a['caseIndex'] not in {c['caseIndex'] for c,_ in picked}):
                picked.append((a,b))
                break
    return picked

schemes={
 'first-per-edge':[rule(i) for i in range(4)],
 'balanced':[rule(0,3,200,.1),rule(1,0,100,.1),rule(2,3,200,.1),rule(3,0,100,.1)],
 'reverse-balanced':[rule(0,0,100,.1),rule(1,3,200,.1),rule(2,0,100,.1),rule(3,3,200,.1)],
 'all-projected':[rule(i,0,100,.1) for i in range(4)],
 'all-midpoint':[rule(i,1,200,.1) for i in range(4)],
 'radius-all-150':[rule(i,0,150,.1) for i in range(4)],
 'radius-all-200':[rule(i,0,200,.1) for i in range(4)],
 'all-quarter':[rule(i,2,150,.1) for i in range(4)],
 'all-threequarter':[rule(i,3,200,.1) for i in range(4)],
}
for label,pattern in schemes.items():
    covered=0
    total_miss=0
    all_4=True
    print('SCHEME',label,flush=True)
    for name,area in sorted(areas.items()):
        chosen=select(area,pattern)
        misses=sum(not b['old_hit'] and b['fixed_hit'] for a,b in chosen)
        total_miss+=misses
        covered+=int(misses>0)
        all_4=all_4 and len(chosen)==len(pattern)
        print(f"  {name}: cases={len(chosen)}, oldmiss={misses}, indexes={[a['caseIndex'] for a,b in chosen]}",
              flush=True)
    print(f"SCHEME_RESULT {label}: diagnostic_areas={covered}/{len(areas)} old_misses={total_miss} all_cases_present={all_4}",flush=True)

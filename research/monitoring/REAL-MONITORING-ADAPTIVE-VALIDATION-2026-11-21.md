# Adaptive OIR fixture validation against real Monitoring — 2026-11-21

## Scope
Only the public research repository `Johnny-Kao/dss-circle-area-research` was changed. The upstream `interuss/monitoring#1911` remains untouched.

## Tested implementation
`research/monitoring/oir_circle_overlap_adaptive.py` is based on the exact current scenario in `Johnny-Kao/monitoring` staging. It uses:
- Real Monitoring `PlanningAreaResource.get_extents` and `Volume3D` circle/polygon footprints;
- The existing Monitoring `_fits` geographic containment check;
- A 17x17 local sampling lattice; S2 source cells sorted by distance to the planning area reference;
- Actual diagonal S2 cell corner selection, distinct-vertex deduplication;
- Enumerated feasible tilts -85..+85 (1 degree resolution), selected by angle quartiles without observing the old DSS oracle;
- Four **distinct** corners, a 300 m OIR circle and 1 m query circle, positive ~0.1 m actual geodesic overlap;
- When four feasible corners cannot fit, a declared `FixtureUnavailable`, never a conformance pass.

Note: no global-optimality proof. This is deterministic and geometry-derived, but scan steps and sample density remain finite constants.

## Real Monitoring shape tests — verified
GC: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44792731636

288 cases: six outline types (circular, square, elongated rectangle, triangle, L-shaped polygon, concave polygon), six scales (500,750,1000,1500,2500,5000 meters), eight geographical reference sites. Genuine Monitoring scenario `_fixtures` and `_fits` were run with parsed `Volume3D` types.

| Shape | 1000 m scale (8 sites) | 1500 m scale | 2500 m scale |
| --- | ---: | ---: | ---: |
| Circle | 1 | 8 | 8 |
| Square | 4 | 8 | 8 |
| Long rectangle | 4 | 8 | 8 |
| Triangle | 0 | 6 | 8 |
| L polygon | 1 | 6 | 8 |
| Concave polygon | 2 | 8 | 8 |

Scale means circular radius, polygon half-extents / overall local construction scale (not equal area). No unexpected exceptions in 288 tests. `FixtureUnavailable` is correctly signaled when four different S2 vertices do not fit.

An additional eight special geographies tested near poles (+/-89.9), dateline (+/-179.9), a S2 face seam and high latitude, with circle/square outlines at 1500 m and 5000 m scales, full 8/8 for all four combinations (32 cases). GC: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44793030828

## HTTP API testing
A first attempt had mismatched old scenario documentation and failed before querying. The scenario code and docs are now aligned with current PR #1911. One true old-DSS v0.23.0 HTTP Red test succeeded with an actual `Overlapping OIR was missing` check and no execution error:
https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44792662440

Full five-offset Red and Green runs:
- Red: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44792648124
- Green: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44792654672

Their completion needs separate verification; do not claim that 10/10 are green solely from the local geometry tests.

## Interpretation
This is a *conditionally generalizable* fixture-generation method, not an all-configurations universal guarantee. Geometry must allow four independent corners and full placement of both circles; small/irregular areas can be unsuitable. No amount of angle selection can logically guarantee the same four distinct corners fit arbitrary very small areas.

Further verification needed before replacing upstream -30-degree constant: complete five-area HTTP Red/Green CI, any actual conformance scenario documentation updates, and quantify choice complexity relative to maintainer-accepted +/-30 degrees.

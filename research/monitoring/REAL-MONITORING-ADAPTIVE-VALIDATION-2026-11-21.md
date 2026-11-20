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

Final verified completion: five old-DSS Red jobs all SUCCESS (each confirms a clean expected `Overlapping OIR was missing`), and five fixed-DSS v0.24.0 Green jobs all SUCCESS, for 10/10 HTTP matrix jobs. These are five spatially shifted instances of the configured rectangular PlanningArea, **not** every polygon/circle shape exercised over HTTP.

Additional scenario syntax, Ruff format/lint, direct Monitoring fixture geometry and upstream documentation validator completed successfully: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44793459953

## Interpretation
This is a *conditionally generalizable* fixture-generation method, not an all-configurations universal guarantee. Geometry must allow four independent corners and full placement of both circles; small/irregular areas can be unsuitable. No amount of angle selection can logically guarantee the same four distinct corners fit arbitrary very small areas.

Further verification needed before replacing upstream -30-degree constant: complete five-area HTTP Red/Green CI, any actual conformance scenario documentation updates, and quantify choice complexity relative to maintainer-accepted +/-30 degrees.

## Upstream resource contract and fixture uniqueness audit (additional review)
Read upstream `monitoring/uss_qualifier/resources/planning_area.py`, `resources/geospatial.py`, scenarios README, test configs, and PR #1911's own scenario docs. Generic `PlanningAreaResource` defines a geographic test volume and does NOT specify a global 300m minimum radius, four S2 corner vertices, or any fixed bounding-area size. The *scenario documentation* from `Johnny-Kao/monitoring` staging specifically requires four distinct S2 corner intersections and says insufficient configuration is unsuitable, not DSS conformance failure. This is a scenario-specific prerequisite (created by this PR), not a pre-existing project-wide hidden contract. Standard Kentland and Zurich planning areas are generous representative examples, not universal required minimums.

A direct fixture identity check against 288 real PlanningArea shape/scale/site cases found:
- Original fixed -30° generator: 171 configurations returned four fixtures, but **107/171** contained duplicated physical S2 corner vertices; **64/171** had four distinct corners.
- Adaptive unique-corner generator: 152 configurations returned four fixtures, and **0/152** contained duplicated vertices.
- This is a mismatch between original scenario documentation and original implementation, **not** a DSS defect. Four distinct vertices is stricter than merely four valid fixtures and changes domain availability.

Public GC: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44795053472

## Computational cost / caching
Measured in the same GitHub Actions runner over the same 288 actual Monitoring shapes. First unoptimized run:
- Fixed baseline total 1.270160s, median 3.898ms, P95 8.618ms.
- Adaptive total 13.961600s, median 56.318ms, P95 100.360ms.
Run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44794478770

Optimized adaptive caches the polygon and the two inward geometric buffers once per PlanningArea in a single `_fixtures` call instead of reconstructing them for each angle:
- Controlled run: fixed baseline total 0.559204s, median 1.719ms, P95 3.627ms; adaptive total 2.614510s, median 9.425ms, P95 16.485ms.
- 4.7x aggregate runtime cost for adaptive in that run, despite major improvement. Shared runner variability affects absolute times, so same-run relative comparisons matter.
- Another same-run fixture-identity GC recorded adaptive 5.761511s and fixed 1.275223s over 288, approximately 4.5x ratio.
Run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44794848583

## Decision
Do not silently turn insufficient fixture geometry into either a DSS conformance failure or a pass. Neither the DSS nor generic PlanningAreaResource contract requires four distinct S2 vertices. The scenario documentation should match the actual desired testing contract (four valid test configurations vs four unique physical vertices), with explicit configuration preconditions. Until that product decision is made, calling adaptive universally superior would be incorrect. A richer angle selector still has code complexity and ~4.5–4.7x fixture-generation runtime cost on these shapes, but test-runtime impact across actual HTTP operations needs separate overall measurement.

## Cached adaptive HTTP regression re-verification
After introducing polygon erosion caching in `oir_circle_overlap_adaptive.py`, the true Monitoring end-to-end HTTP matrices were run again:
- Historical DSS v0.23.0 Red: **5/5 success**, each workflow explicitly detects missing genuinely overlapping OIR without execution error. https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44794848686
- Fixed DSS v0.24.0 Green: **5/5 success**, no unexpected conformance failures. https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44794848612
- Real Monitoring geometry and documentation CI: success. https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44795053472

These establish that the caching optimization preserved the expected 5-area HTTP Red/Green checks, **not** a proof that arbitrary tiny planning areas can support four unique vertices.

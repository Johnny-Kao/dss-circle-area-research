# PR #1911 — v4 adversarial true-circle witness: Research result

Status as of 2026-11-17 (Japan), **Research only**. No Staging or Upstream writes.

## Issue addressed

The v2 candidate checked real-circle overlap but selected the first valid S2 edge. In real old DSS API tests this could pass even with the historical omission bug. v3 searched four edge orientations: it reliably caught old bugs in the five original areas but only 19/32 additional areas. Trying to enforce four historically diagnostic **edge orientations** is an incorrect requirement: in some areas only certain orientations admit a legacy-inscribed-polygon-vs-true-circle gap.

## Implementation

Branch: `research/pr1911-adversarial-witness-v4`

Scenario: `research/monitoring/oir_circle_overlap_standalone.py`

- Construct true circular OIR and 1m circular query with actual positive overlap across S2 Level 13 boundary.
- **Fixture filter only**: reproduce the historical `s2.RegularLoop` 20-sample tangent frame and confirm its sampled vertices all remain in the source Cell.
- Select up to four **distinct** candidate source/edge/offset placements, prefer distinct S2 source cells but permit additional valid positions in the same source cell when needed.
- Conformance assertion *only* checks ASTM DSS0005,2: returned results must include a genuinely intersecting OIR. Extra false-positive search results are permitted. No polygon is submitted to DSS.
- No fixed geographic coordinates and no dependence on old DSS responses at runtime.
- Fail explicitly with `FixtureUnavailable` if the configured Planning Area cannot supply four historically diagnostic placements; do not claim a false passing regression.

The historical polygon filter is intentionally implementation-specific. This branch is a *known-bug-focused* fixture generator, **not** fully vendor-independent scenario design. Review for upstream suitability before any Staging or PR changes.

## Evidence

- Research-only v4 target contract on five existing regions: **5/5 areas**, **four selected fixtures each**; independent old Go S2 index misses **20/20**, fixed index finds **20/20**. Test includes positive ASTM assertions and missing-OIR fault injection.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43901823829
- 32 additional Planning Areas: **NOT 32/32**. For example case-01 (center lat -12, lon -97, 6km x 3.3km) has **zero** accepted historically diagnostic boundary placements even with tested OIR radii 100/150/200m, several edge fractions, depths 0.11/0.05/0.02/0.005m, and 0.001m query clearance.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43901823925
  This does **not** mean the ASTM real-circle test is incorrect; it means the *historic vendor defect* is not guaranteed to be observable at every arbitrary site. A mathematical universal witness guarantee is **not** established.
- Original generic v3 scenario continues to generate valid true-circle test fixtures in **32/32** additional areas, but old historical-bug sensitivity was **19/32**.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43887513123
- **Final v4 source** (commit `84c8ca59128a9bd55e5b9dba66171f21576afe53`) passed
  the original project-wide `make check-hygiene`: **SUCCESS**.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43902711683
- **Final v4 source** passed real DSS API **6/6 matrix jobs**: old DSS
  Stanford/Kentland **expected RED**, patched DSS Stanford/Kentland
  rectangle and Kentland concave-L/circle **GREEN**.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43902711588
- Final Research contract **SUCCESS** (5 existing regions x four individually
  historical-diagnostic witness fixtures; independent old covering misses all
  20, fixed covering finds all 20; API assertion fault injection).
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43902711542
- A prior real API run found an unrelated helper error
  (`oir_circle.radius.in_meters()` was incompatible with the returned string
  units); corrected to `oir_circle.radius.value`, rerun passed all six jobs.
- No mathematical or test-based proof that **every arbitrary Planning Area**
  has four historically diagnostic circular witnesses; the 32-region
  universal-RED attempt remains **FAILED**. This is a real portability limit,
  not a failure of ASTM positive-result assertion.

## Engineering conclusion

Two materially distinct goals must not be conflated:

1. **ASTM conformance**: generate genuinely intersecting true-circle 4D cases in a Planning Area and assert OIR presence. No historical vendor geometry is needed. v3 is the stronger portable candidate.
2. **Guaranteed reproduction of the historical 20-vertex index omission**: must construct and prove an old-index miss where possible. v4 supplies a validated witness *conditionally*; it explicitly rejects incompatible Planning Areas rather than silently passing.

Do not present 20/20 fixtures from the original five areas as proof that a universal vendor-neutral regression witness exists for every possible Planning Area. Do not update public PR #1911, Staging, or upstream without explicit authorization.

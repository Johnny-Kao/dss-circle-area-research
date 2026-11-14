# PR #1911 — Contract-first cross-cell search experiment (2026-11-14)

## Contract and fixture

- The only API-level search assertion is positive: a registered circular OIR that genuinely overlaps a circular query in space, altitude, and time must be found.
- A false-positive return for a non-overlapping OIR is permitted under ASTM F3548-21 and is not asserted as a failure.
- The query circle B is not registered. The generator picks a level-13 S2 cell edge within the runtime PlanningArea, places B wholly in the neighboring cell, and computes circle A's position from the requested overlap depth rather than reconstructing the removed legacy 20-gon.
- Current parameters: B radius 1 m, clearance from cell edge 0.1 m, desired radial overlap 0.5 m; A radius tries 200, 150, 100, 50 m within the PlanningArea.
- Output correctness uses independent great-circle center separation, not S2 covering intersection. The parent research scenario still contains legacy-only helpers, because the new generator is an isolated subclass prototype, not a maintainable upstream patch.

## Evidence

**Geometry CI:** [run 43599562156](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43599562156) — PASS. Across 11 geographical locations and 5 area shapes (55 fixtures): rectangles 11/11, concave L shapes 11/11, 1.5 km-radius circles 11/11. Tiny 100 m footprints 0/11 and 50 m-wide corridors 0/11 are explicitly reported as inapplicable. This is **33/55** actual boundary fixtures, not 55/55.

**Real DSS API red/green CI:** [run 43599717962](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43599717962) — mixed:
- Kentland old DSS: **Red**, overlapping OIR missing.
- Kentland fixed DSS: **Green**, OIR found.
- Stanford old DSS: **Green**, OIR found; this test did **not** detect the original bug there.
- Stanford fixed DSS: **Green**, OIR found.

The expected-old-Red CI correctly fails at Stanford. This failure is **diagnostic**, not an infrastructure error.

## Decision / open questions

- The design meets the external search contract for constructed positive-overlap fixtures, but a cross-cell overlap does not guarantee the original 20-gon bug is exposed. Thus this version does **not yet meet** Benjamin Pelletier's stronger requirement for a deliberately diagnostic adversarial fixture.
- In small planning areas there may be no useful level-13 S2 boundary at all. A scenario-level inapplicable note must be surfaced by the suite gate, not accepted as an ordinary green regression.
- The current subclass imports the previous 370-line research scenario and is **not** an acceptable minimal upstream implementation.
- Next step before Staging: choose explicitly between (a) contract-first positive overlap testing, which does not guarantee old Red, and (b) maintaining a diagnostic old-Red guarantee, which requires additional construction/certification of the previously omitted region.
- No Staging or upstream change was made.

# PR #1911 merge-readiness audit (2026-11-15)

Scope: **Research-only review** of `research/pr1911-maintainer-wording-polish`. No edits to staging, the upstream PR, or the scenario candidate.

## Evidence checked

- Upstream: [interuss/monitoring#1911](https://github.com/interuss/monitoring/pull/1911): one high-level review plus 17 inline threads (all unresolved on the unchanged PR head). The high-level review asks for a constructed S2-boundary case, not opportunistic circular overlaps.
- Original fix: [interuss/dss#1914](https://github.com/interuss/dss/pull/1914): legacy `s2.RegularLoop(center, angle, 20)` replaced with `s2.CapFromCenterAngle(center, angle)`.
- Candidate: [317-line standalone scenario](https://github.com/Johnny-Kao/dss-circle-area-research/blob/research/pr1911-maintainer-wording-polish/research/monitoring/oir_circle_overlap_standalone.py), plus its [scenario documentation](https://github.com/Johnny-Kao/dss-circle-area-research/blob/research/pr1911-maintainer-wording-polish/research/monitoring/oir_circle_overlap_standalone.md).
- Existing independent differential oracle: [Go checker](https://github.com/Johnny-Kao/dss-circle-area-research/blob/research/pr1911-differential-fixture-finder/research/monitoring/differential_s2_cover_oracle.go); this already compares the true legacy and fixed covering algorithms outside the production-facing scenario.
- GitHub Actions [wording regression run](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43712356273): 7/7 jobs succeeded (including old/fixed DSS checks). [Full suite acceptance](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43710575288) compares baseline and candidate rather than equating the overall exit code with a regression.

## Findings

1. **The fixture generator does not independently guarantee the legacy witness.** The candidate verifies primary-center and query-circle S2 placement, true-circle overlap, and planning-area containment; it does **not** explicitly verify that the historical 20-sided covering misses that query cell. This is acceptable as a design goal for an implementation-independent conformance scenario, but it means 'each fixture diagnoses the historical bug' is not established. Use the existing *Research-only* Go differential oracle to evaluate each emitted fixture, not a 20-sided oracle inside the submitted scenario.

2. **The first four usable fixtures can be redundant.** `MAX_FIXTURES=4` returns the earliest four qualifying cases without requiring distinct edges/cells or independent diagnostic outcomes. Prior Kentland/Stanford results show why simply choosing the first case is unsafe. Count both actual API checks and *distinct* diagnostic witnesses before reducing the set. Four pass checks are not equivalent to four independent edge configurations.

3. **Tiny overlaps warrant a cross-implementation tolerance test.** The scenario uses `OVERLAP_DEPTHS_M=(0.5,0.1)` with 1 m query circles. Monitoring's `scenario.py` contains a 0.7% distance-error allowance for certain threshold checks because spherical models differ; this is **not** an ASTM-authorized tolerance for OIR intersection and should not be applied mechanically. Nonetheless it warns against treating sub-meter overlap as a robust interoperability witness without testing alternative distance models, coordinate precision, and circle serialization. A 200 m scale × 0.007 = 1.4 m, larger than either configured depth.

4. **There is a narrow geometric feasibility window.** The maximum radial sagitta of an inscribed regular 20-gon is `r*(1-cos(pi/20)) ~= 0.0123117*r`, **an upper bound**, not the guaranteed gap in the actual S2 edge direction. Illustrations: r=200 m => ~2.46 m; r=300 m => ~3.69 m; r=700 m => ~8.62 m. Larger overlaps might reduce cross-model fragility, but must still be independently demonstrated to cause the old miss. Increasing every radius to the review's earlier 700-1100 m example is not automatically viable: DSS uses level-13 cells, with default cells around ~1 km².

5. **Documentation and implementation terminology should be tightened.** `_fixtures()` says 'without assuming a DSS index design', yet it hardcodes `CELL_LEVEL=13`. The S2 layout is a *Research-supported fixture strategy*, not an ASTM conformance requirement. Explain that distinction briefly in the PR description and avoid an over-broad independence claim in source comments.

6. **Unavailable fixtures are an execution/configuration outcome, not a failing DSS check.** The latest candidate raises `FixtureUnavailable` before entering the test case; an earlier Research version caught this and recorded `test_inapplicable`. Ensure the current uncaught outcome matches the Monitoring runner's intended reporting behavior; a green no-search run must never be reported as conformance PASS.

7. **The original PR description must be replaced when staging is approved.** It still asks to keep negative assertions, which the reviewer correctly found unsupported by ASTM F3548-21, and still says the complete `dss_probing` suite has not run. Update once along with the final diff; do not reply to or resolve review threads prematurely.


## Reproduced model-sensitivity counterexample (independent calculation)

Method: start from the same latitude/longitude center, place a second center **due east** at a spherical great-circle distance of `primary_radius + query_radius - depth`, using `R=6,371,010 m` (the DSS sphere). Independently measure that pair using the WGS84 ellipsoid geodesic (Python GeographicLib 2.1). A negative inferred overlap means the circles are disjoint **under that alternative earth model**, not that either implementation violated ASTM.

All values below use primary radius 200 m and query radius 1 m; values are in meters.

| Latitude | Spherical intended overlap | WGS84 center distance | WGS84 inferred overlap |
|---|---:|---:|---:|
| 35.68° (Tokyo) | 0.1 | 201.354 | -0.354 |
| 35.68° (Tokyo) | 0.5 | 200.953 | +0.047 |
| 47.38° (Zurich) | 0.1 | 201.490 | -0.490 |
| 47.38° (Zurich) | 0.5 | 201.089 | -0.089 |
| 60.17° (Helsinki) | 0.1 | 201.633 | -0.633 |
| 60.17° (Helsinki) | 0.5 | 201.232 | -0.232 |
| 81° | 0.1 | 201.785 | -0.785 |
| 81° | 0.5 | 201.383 | -0.383 |

**Interpretation:** The candidate's sub-meter overlaps are not robust to a plausible change of Earth-distance model. The exact applicable circle metric under ASTM F3548-21 needs confirmation; the public OpenAPI describes a circular area on the Earth's surface without resolving the sphere-versus-ellipsoid semantics in that description. Do **not** infer actual DSS noncompliance from this calculation. Rather, do not make a universal conformance claim until a deliberately conservative margin has been checked against the protocol and the historical-regression requirements.

Possible precision-safe experiment (Research-only): attempt larger overlaps and/or radii with the existing Go differential oracle, then confirm real API Red/Green without adding legacy logic to the production test. Evaluate across multiple headings, not only the due-east counterexample. If the ASTM circle model is explicitly spherical, document that constraint and revise this concern accordingly.

## Smallest next research experiment

Keep the production candidate unchanged. For each of the four emitted fixtures in Kentland and Stanford:
- Check actual query/OIR circles have a positive overlap under the intended model.
- Run the existing independent Go old/fixed covering oracle on exactly those fixture coordinates, identifying the diagnostic witnesses.
- Calculate sensitivity to modest model/coordinate changes and try overlaps larger than 0.5 m **in Research only**, within the actual old-20-gon gap.
- Prefer one or two **independent, stable** witnesses per run if they continue to give old Red / fixed Green across the same area and shape matrix.
- If this fails, retain four fixtures and explain why. Avoid new permanent S2/legacy logic in the formal scenario.

## Acceptance gate before upstream update

- Old DSS Red due to a **missing overlapping OIR**, not a scenario/runner error; fixed DSS Green, and actual API queries executed.
- Distinct fixture/witness coverage and precision sensitivity checked.
- Rectangular, concave-L, and circular Planning Area checks retained; unavailable geometry is not a false Green.
- `make format`, `make lint`, generated scenario/suite documentation, and full `dss_probing` baseline-vs-candidate comparison pass without additional failures.
- Changes and comments are kept brief and mapped to the reviewer's intent. Upstream not touched without explicit approval.

**Decision:** Current candidate is a proven regression scenario in tested environments, **not yet a minimized reviewer-ready implementation**. Prioritize deterministic diagnostics and geometric robustness over nominal line count.

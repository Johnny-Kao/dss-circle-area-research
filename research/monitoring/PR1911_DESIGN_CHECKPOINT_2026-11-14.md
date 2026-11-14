# PR #1911 — Research design review checkpoint (2026-11-14)

## Decision

**ASTM output contract:** a circular registered OIR that genuinely overlaps the query in horizontal footprint, altitude, and time MUST be found. Non-overlapping OIRs may be returned; do NOT assert their absence.

**Test case:** use a valid PlanningAreaResource to create exactly one registered circular OIR A and one small query circle B. Verify the true great-circle overlap independently. Query the live DSS through the ASTM API and assert A appears. Cleanup always removes the test OIR.

**Diagnostic fixture:** select an actual S2 cell edge, put B fully inside a neighboring cell, and place A's true circular edge slightly beyond that S2 boundary. On the research branch, also certify that an inscribed, 20-vertex approximation would stay in the original cell. This *setup-only research witness condition* is not the API PASS/FAIL rule. It makes the test intentionally adversarial, as explicitly requested by the maintainer, and still permits any conforming DSS implementation to pass.

**Portability:** never hard-code geographical coordinates in the scenario. Check entire circle footprints against the planning area, not only the bounding box. Do not silently substitute a generic overlap on fixture failure. Report inapplicable explicitly; the Research CI also fails if an intended geometry is inapplicable.

## Verified evidence

- [Geometry and linter CI — success](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43602317404). 11 geographically diverse locations x 5 shape types; diagnostically certified: rectangle 8/11; concave L 8/11; circle 8/11. Tiny footprints and narrow corridors 0/11; declared inapplicable rather than counted as passes.
- [End-to-end CI with research prototype — success](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43601547256). Four expected outcomes: old Kentland Red, old Stanford Red, fixed Kentland Green, fixed Stanford Green.
- [End-to-end CI with independently implemented candidate — success](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43603258448). Same 4/4 expected outcomes. This tests the standalone Python scenario plus the corresponding standard-facing documentation.

## Files

- `research/monitoring/oir_circle_overlap_standalone.py`: standalone candidate, 291 LOC.
- `research/monitoring/oir_circle_overlap_standalone.md`: standard-facing scenario documentation, with warning-level positive-overlap check, no InterUSS-specific historical details.
- `research/monitoring/oir_circle_overlap_contract_first.py`: compact research prototype that relies on prior experimental utility code.
- CI workflow `.github/workflows/pr1911-review-red-green.yml` runs actual DSS HTTP APIs with isolated Monitoring checkout and standalone candidate, without touching upstream.

## Remaining constraints before staging

1. The standalone candidate still uses a 20-point inscribed reference in **fixture construction**, and S2 Level 13. The actual API assertion is independent of this historical implementation. If the project forbids even a historic approximation as fixture-generation input, then **a universal old-Red guarantee cannot simultaneously be claimed** with this simple construction. A truly implementation-agnostic test can still test the ASTM contract, but its older-version diagnostic coverage is not guaranteed.
2. A diagnostic fixture is not always possible in small or awkward planning areas; these must be reported inapplicable and not silently accepted as green.
3. 291 LOC is a research-verified candidate, NOT an approved final minimum-LOC upstream patch; maintainer-facing code reduction and full-suite integration remain optional pre-staging review.
4. No Staging or Upstream changes were made.

**State:** Research standalone scenario + docs complete; geometric and real API validation pass. No automatic promotion or submission.

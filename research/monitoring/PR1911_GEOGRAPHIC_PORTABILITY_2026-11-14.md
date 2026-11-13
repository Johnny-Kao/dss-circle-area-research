# PR #1911 — Multi-planning-area real DSS Red/Green verification

Date: 2026-11-14 JST. Scope: Research branch only.

## Objective

Validate the *same* automatically generated S2-edge overlap scenario across independent planning-area locations, not a Kentland-specific hardcoded fixture.

## Results — real Qualifier and DSS API

**Nearby shifted areas:** [Actions run 43497045005](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43497045005)

- Five planning-area offsets (0, east 10 km, south 10 km, west 10 km, north 10 km)
- Old DSS (`interuss/dss:v0.23.0`): 5/5 Red detection jobs successful
- Fixed DSS (from `Johnny-Kao/dss@staging/pr-1914-review-final`): 5/5 Green jobs successful
- Matrix: **10/10 GitHub Actions jobs succeeded**.

**Geographically separated areas:** [Actions run 43497785005](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43497785005)

- Five CI-only test-area placements: Kentland (37.20005, -80.579), Tokyo (35.68, 139.75), Zurich (47.38, 8.54), Helsinki (60.17, 24.94), Stanford (37.43, -122.17)
- Old DSS: 5/5 jobs successfully verified missing overlapping OIR (Red).
- Fixed DSS: 5/5 jobs returned overlapping OIR and passed (Green).
- Matrix: **10/10 GitHub Actions jobs succeeded**.
- Location coordinates occur **only in CI fixtures**, not in the scenario; scenario reads `PlanningAreaResource.get_extents()`.
- Workflow generates one boundary case dynamically via `s2sphere`, runs the Monitoring Qualifier against a real DSS image, excludes scenario execution errors, and archives logs/reports.

## Interpretation

This provides good evidence that the current scenario does not depend on one GPS location. It is still **not** proof that every valid `PlanningAreaResource`, all latitudes (including poles), antimeridian-spanning regions, or very small regions will work.

## Important remaining design tradeoff

The current *input generator* is **InterUSS-implementation-specific**: it assumes S2 cell level 13 and old 20-vertex inscribed polygon when constructing an adversarial case. The *pass/fail assertion* is vendor-neutral and based on the ASTM F3548-21 no-false-negatives requirement.

This split is crucial. A true generic conformance test must not make success of a different ASTM-conforming DSS depend on emulating InterUSS internals. Maintainer explicitly wanted an adversarial S2 boundary to diagnose this regression, so the generator may be justified as a targeted regression fixture, but this should be clarified before presenting it as a general-purpose ASTM test. Avoid false claims of universal portability.

## Further design gates

1. Assess what subset of planning areas the scenario reasonably supports and fail with clear preconditions (not misleading test errors).
2. Verify actual circle vs query overlap survives coordinate serialization and is not a marginal floating-point artifact; log measured overlap margin.
3. Reduce `_CIRCLE_CONFIGURATIONS` and samples only if resulting cases retain geographic Red/Green reliability and safety margins.
4. Update Markdown to timeless ASTM requirements and match all test steps; remove invalid negative assertions from documentation.
5. Don't promote changes from Research until approved.

Research workflow: `.github/workflows/pr1911-review-red-green.yml`; scenario: `research/monitoring/oir_circle_overlap_review.py`. Staging and upstream untouched.

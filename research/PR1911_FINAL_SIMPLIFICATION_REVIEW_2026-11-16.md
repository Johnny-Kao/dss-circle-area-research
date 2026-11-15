# PR #1911 — Final code simplification review
Date: 2026-11-16 JST. Scope: Research only; neither Staging nor Upstream was modified.

## Source of truth
- Verified candidate: `research/pr1911-contract-acceptance` — **337 Python lines**.
- Simplified candidate: `research/pr1911-final-simplification` — **334 Python lines**, commit `d8a3f1d`.
- Upstream guidance: `interuss/monitoring` PR #1911 (17 inline review threads, plus BenjaminPelletier high-level review) and `monitoring/uss_qualifier/scenarios/CONTRIBUTING.md`.

## Accepted changes and why

1. **Hoist query-circle invariants outside the radius/depth loop.** For any given S2 edge position, the query center, its neighbor Cell ID, its whole-circle containment, and its PlanningArea containment do not depend on the five OIR radii or two overlap depths. Previously these query-side calculations could run **up to 10 times for the same position**. Now each is checked once. The OIR radius/depth loop and fixture iteration order are unchanged.
2. **Make the returned OIR handle a local variable.** `self._created_oir` was only read during deletion in the same `run()` iteration; initialization and resetting to `None` had no effect on `cleanup()`, which uses `self._oir_id` and the existing `cleanup_op_intent` fragment. `created_oir` expresses this limited lifetime and removes two redundant state assignments.
3. **Use existing project geometry API.** `source.center.as_s2sphere().to_point()` replaces hand-written `s2sphere.LatLng.from_degrees(...).to_point()`. `LatLngPoint.as_s2sphere()` is defined in `monitoring/monitorlib/geo.py` and performs the identical conversion.

**Net: −3 physical Python lines.** The value is reduced repeated work and simpler object lifetime, not the line count alone. No changes to radii, overlap depths, requested scenarios, check severities, requirements, or documented tests.

## Reviewed and deliberately retained
- `_legacy_loop_inside_cell`: necessary to deterministically construct the exact adversarial geometry requested by the maintainer. Removing it previously allowed nominally crossing fixtures without a true old-DSS miss.
- `_circle_in_cell`: checks whole query-circle containment, not only which Cell holds its center.
- `_fits`: honors the true PlanningArea circle or polygon footprint, including concave areas.
- `_check_found`: checks positive OIR inclusion, tolerates false positives, and reports failed HTTP calls.
- Explicit `begin_test_step` calls: match project's scenario-documentation validation and keep reviewers' expected test-step names obvious.
- Multiple radius/depth choices: earlier simplification experiments lost diagnostic power in some regions.
- No special-case hardcoded geographic coordinates in the production-facing Scenario; independent Research CI uses named regions only as fixtures.
- Do not add area-outline memoization or caches in this PR: the saved lines are unlikely to justify new state or complexity. Remaining Shapely buffer work is a possible future performance concern, not a correctness flaw established here.

## Reproducible gates
- [Contract acceptance run 43732525960](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43732525960) — passed: 5/5 behavioral/fault-injection unit tests, all 20/20 **actual selected** cross-implementation Go S2 diagnostic fixtures (4/4 each in Kentland, Stanford, Tokyo, Zurich, Helsinki), Ruff format/lint, and native Monitoring scenario-doc validation.
- [Actual DSS API run 43732530726](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43732530726) — verify completion before accepting the simplification. Required: old Kentland/Stanford reliably RED due to missing overlap; fixed Kentland rectangle/concave-L/circle and Stanford rectangle GREEN.

## Limitations / release gate
- Exact behavior across other DSS geographic models was not established. The 0.1m/0.5m overlap margins are narrow; do not claim universal ellipsoidal robustness.
- The native full `dss_probing` earlier had **existing** DSS0300 public-addressability failures in Docker mock environments for both Baseline and Candidate. Targeted passing gates do not imply a clean full-suite exit.
- The upstream PR description and unresolved review threads still refer to an older candidate, and will require an authorized, cohesive update.
- **Acceptance rule:** adopt this Research change only if the real DSS API matrix remains fully green; otherwise retain the verified 337-line candidate and do not propagate this branch.

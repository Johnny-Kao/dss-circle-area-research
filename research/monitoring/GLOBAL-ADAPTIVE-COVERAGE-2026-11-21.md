# Global S2 Corner Adaptive Geometry Research — 2026-11-21

## Scope and safety
Research only for interuss/monitoring PR #1911. **No upstream PR, issues, or source changes**. Source experiments are in this public repository. Baseline oracle: historical `interuss/dss@e97e15eccbe87d114cf85892db6f675e05b93311`, using production `GeoCircle.CalculateCovering`.

## Global sampling
- 10,000 deterministic approximately equal-area global locations (`lat = asin(2u-1)`, longitude from an irrational-step sequence); additional 15 targeted polar, dateline, S2 Face orientations/intersections.
- The standard global sample uses local latitude 0.026° × longitude 0.060° sampling envelopes **without enforcing a complete PlanningAreaResource outline**. Thus this is geographical algorithm coverage, not a universal statement about any configured testing area.
- Fixture construction: exact level-13 S2 diagonal-cell relationship, 300 m OIR, 1 m query circle, ~0.1 m true overlap, four fixtures total. Adaptive searches feasible integer-degree tilts between -85° and +85° and chooses quartiles by fixture index, without querying the old oracle to select the angle.
- In the adaptive path, the corrected `s2.Cap` coverings must also intersect. This is a geometric positive control, **not an end-to-end HTTP patched-DSS test**.

## GC verified comparisons
Run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44789805261

| Policy | Valid four fixtures / 10,000 | At least one legacy omission / 10,000 |
| --- | ---: | ---: |
| Fixed -30° | 10,000 | 9,747 |
| Fixed +30° | 10,000 | 9,754 |
| Mixed -30° then +30° | 10,000 | 10,000 |
| Adaptive feasible-angle quartiles | 10,000 | 10,000 |

All six S2 faces represented approximately equally. All sampled latitude bands succeeded; additional special probes included 89.99° N/S, ±179.999° longitude and representative face boundaries.

## Circle-shaped planning-area constraints
Unlike the standard global test, these 300 locations per radius check that the complete OIR and query circles (plus 1 m margin) remain inside a spherical circular planning area centered at the reference location.

| Planning area radius | Four fixtures constructible / 300 | At least one old omission / 300 |
| --- | ---: | ---: |
| 350 m | 0 | 0 |
| 500 m | 3 | 3 |
| 750 m | 153 | 151 |
| 1000 m | 300 | 299 |
| 1500 m | 300 | 300 |
| 2500 m | 300 | 300 |
| 5000 m | 300 | 300 |
| 10000 m | 300 | 300 |

These figures identify a real practical issue: a geographically universal fixture method is not necessarily usable in very small planning areas. Sampling/search may also influence the failure rate; these numbers are **not** proven mathematical minimum-size bounds.

## Conclusion
Adaptive and dual ±30° are tied at 10k/10k legacy-error captures with a strict four-fixture budget. Adaptive has a geometry-derived rationale but more code and candidate-search work. Neither is mathematically proven optimal or exhaustive, and failures remain in constrained planning areas. Do not claim all worldwide locations and configurations are covered.

## Follow-up validation before any upstream change
1. Evaluate the adaptive generator under the actual Monitoring `PlanningAreaResource` types and `_fits` behavior, including polygons, small and elongated areas, and edge/face crossing.
2. Exercise old-DSS Red and patched-DSS Green via real HTTP APIs; perform full Monitoring CI.
3. Compare construction cost and maintainability against the already-approved simple ±30° proposal.
4. Keep the upstream PR untouched until explicitly approved.

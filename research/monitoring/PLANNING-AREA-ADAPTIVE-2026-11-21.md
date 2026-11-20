# Planning-Area Adaptive S2 Corner Research — 2026-11-21

## Research boundary
Public research only. No changes to interuss/monitoring PR #1911, no upstream pushes. Legacy oracle is the actual historical production `GeoCircle.CalculateCovering` at DSS e97e15eccbe87d114cf85892db6f675e05b93311. The spherical-cap intersection is used as a corrected-geometry positive control, not a live HTTP green test.

## Major finding
The original fixture generator stops after four candidates but does not explicitly require *four distinct S2 vertices*. Adjacent cells can reference the same vertex. Four fixtures may consequently provide fewer than four independently positioned corner sites. This matters especially in small PlanningAreas.

Research comparison: 300 deterministic areas per specified radius; full large/small circular coverage enforced by geodesic center distance plus radius + 1 m margin. The alternate generator enumerates 17x17 lat/lng samples, selects feasible angles using actual S2 cell geometry, and deduplicates vertices using 11-decimal lat/lng keys. Candidate cells are sorted by distance to the planning-area reference, not by CellID. It does not use the legacy oracle to select fixtures. The candidate `Cell.Center` prefilter was removed because it incorrectly eliminated cells with legal corner geometry.

### Four distinct vertices vs legacy four fixtures
| Circular PlanningArea radius | Legacy four fixtures / 300 | Four distinct corners / 300 |
|---|---:|---:|
| 350m | 0 | 0 |
| 450m | 1 | 0 |
| 500m | 3 | 0 |
| 650m | 42 | 0 |
| 750m | 153 | 0 |
| 850m | 262 | 1 |
| 1000m | 300 | 32 |
| 1500m | 300 | 298 |
| 2500m | 300 | 300 |

These counts are empirical with this generator and sampling plan, **not** a mathematically proven lower bound on PlanningArea size.

### Adaptive test budget: maximum distinct vertices possible (0–4)
Run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44790989788

| Radius | 0 fixtures | 1 | 2 | 3 | 4 | With >=1 | Areas with >=1 legacy omission |
|---|---:|---:|---:|---:|---:|---:|---:|
| 350m | 259 | 41 | 0 | 0 | 0 | 41 | 30 |
| 450m | 167 | 131 | 2 | 0 | 0 | 133 | 98 |
| 500m | 129 | 168 | 3 | 0 | 0 | 171 | 127 |
| 650m | 28 | 236 | 36 | 0 | 0 | 272 | 210 |
| 750m | 5 | 168 | 125 | 2 | 0 | 295 | 251 |
| 850m | 0 | 98 | 171 | 30 | 1 | 300 | 274 |
| 1000m | 0 | 26 | 168 | 74 | 32 | 300 | 288 |
| 1500m | 0 | 0 | 0 | 2 | 298 | 300 | 300 |
| 2500m | 0 | 0 | 0 | 0 | 300 | 300 | 300 |

## Interpretation / candidate design
A two-stage, geometry-derived strategy is promising:
(1) Find candidate S2 corners whose physically genuine OIR and query circles fit within the actual PlanningArea. Verify unique vertices and genuine 0.1m overlap. Rank by location/angle diversity, **never** by old-index success.
(2) Select up to four *distinct* vertices; record actual count. For formal four-vertex conformance testing, declare an insufficient PlanningArea when fewer than four exist. A separate explicitly documented reduced-coverage mode (1–3 vertices) could still check positive discovery but must never be reported as equivalent to the full four-corner scenario. Avoid silently changing the existing upstream test contract.

## Important limitations
- Current experiment covers *circular* planning areas only. Real `PlanningAreaResource` can also be polygonal; complete Testing/Suite integration and area-shape assertions are not verified.
- Different geographically valid fixtures are not automatically diagnostic against all DSS implementations.
- In smaller areas, adaptive fixture count improves graceful degradation, **not** proof of four distinct corner feasibility.
- Corner diversity by near-equal lat/lng string keys is research-level; production code should use exact S2 CellID/vertex topology or a carefully validated canonical identity.
- Full old-DSS Red, patched-DSS Green HTTP end-to-end and Monitoring CI remain required before any upstream change.
- Existing 10k worldwide sample results use generous test sampling bounds; they do not imply that all shapes and sizes can provide four distinct corners.

## Research code
`research/monitoring/area_aware_adaptive_test.go`
`research/monitoring/global_adaptive_coverage_test.go`
`.github/workflows/corner-tilt-sweep.yml`

## Recommendation
Do not prematurely introduce reduced-coverage behavior into upstream PR #1911; the maintainer already considers its existing four-fixture method mergeable. Preserve the research and, if desired, prototype true PlanningAreaResource-aware discovery on a separate research staging branch first.

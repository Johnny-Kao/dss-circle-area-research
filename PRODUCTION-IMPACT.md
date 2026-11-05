# Production-path review — 2026-11-05

Upstream baseline: `interuss/dss@e97e15eccbe87d114cf85892db6f675e05b93311`

## Reproduced

GitHub Actions run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/41983607486

- 30,000 m Circle (~2,827 km² nominal area) was not rejected in two original geometry paths.
- Regression tests failed as expected on upstream (RED).
- Candidate patch routes generated 20-vertex loops through `geo.Covering`, which enforces `maxAllowedAreaKm2 = 2500.0`.
- Targeted Go tests for `pkg/models`, `pkg/scd/models`, and `pkg/rid/models/api/v2` passed (GREEN).

## Confirmed API reachability in source

1. RID v2: `CreateIdentificationServiceArea` and `UpdateIdentificationServiceArea` -> `apiv2.FromVolume4D` -> `operations.NewInsertISAPayload`/`NewUpdateISAPayload` -> `newISA` -> `Footprint.CalculateCovering`; `GeoCircle.CalculateCovering` bypasses area check.
2. SCD operational-intent create/update: `NewCreateOIRPayload`/`NewUpdateOIRPayload` -> `newOIRUpsert` -> `UnionCellsVolume4DFromSCDRest` -> `CellsVolume4DFromSCDRest` -> `circleCellsFromSCDRest`. This parser bypasses area check.
3. SCD subscription create/update: `NewCreateSubscriptionPayload`/`NewUpdateSubscriptionPayload` -> `newSubscription` -> `CellsVolume4DFromSCDRest`.
4. SCD queries (operational intents, subscriptions, constraints) use `CellsVolume4DFromSCDRest` for supplied area of interest.

## Potential downstream effects (not yet demonstrated end-to-end)

- Larger than intended query/search area and higher spatial index and DB processing cost.
- Wider-than-intended notification matching and more affected subscriptions on entity writes.
- Unexpectedly broad ISA, operational-intent, constraint, or subscription indexing if other business rules permit.
- Geometry implementation inconsistency (same logical area rejected as polygon, accepted as circle).

## Important limitations

- This is a verified geometry-level invariant bypass and production-reachable source path, **not** yet proof of an end-to-end authenticated HTTP request being successfully committed to a datastore.
- Does not establish anonymous access, flight safety compromise, exploitable denial of service, or real deployed-instance impact.
- The 2,500 km² limit is visible in the implementation; do not claim it is a universal ASTM limit without standards review.
- Candidate patch uses the existing inscribed 20-vertex approximation. Circle boundary coverage remains an independent existing TODO, and boundary/degenerate behavior requires regression review.
- The test suite is targeted, not full integration or end-to-end certification.

## Next validation

Run HTTP handler + datastore integration coverage on a disposable GitHub Actions environment, compare accepted vs rejected responses, and exercise a boundary matrix around 2,500 km². Inspect standard constraints and upstream intent before filing a PR.

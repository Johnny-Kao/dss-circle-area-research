# Circle boundary undercoverage — reproduced 2026-11-05

Baseline: `interuss/dss@e97e15eccbe87d114cf85892db6f675e05b93311` (unchanged upstream).

## Confirmed geometry-level missed intersection

- First circle center: (37.427636, -122.170502); radius 15,000 meters.
- Second circle center: (37.450505047, -122.003926497); radius 20 meters.
- Second center is strictly inside first geodesic circle (constructed on 99.5%-radius inner ring).
- Production `GeoCircle.CalculateCovering` uses an *inscribed* 20-vertex `s2.RegularLoop`.
- Upstream computed 713 S2 cells for the first circle and one cell for the second circle, **with zero shared indexed S2 cells**.
- Thus two physically overlapping circles can have disjoint DSS S2 cell coverings.

Run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/41990031835

## Alternative geometry control

Using `s2.CapFromCenterAngle` with the same `geo.RegionCoverer`:
- First circle: 726 cells (vs 713 with polygon).
- Second circle: 1 cell.
- **The two coverings intersect**, as real-circle geometry requires.
- At radius 27km, original 20-vertex covering was 2,218 cells vs 2,255 for cap; 37 cap-only cells. This is not a physical area-difference percentage.

Run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/41990267143

## Interpretation

**Confirmed:** this is an S2 spatial-index false negative for physically overlapping circles, in the code shared by production RID and the separately implemented SCD circle path.

**Potential downstream implication:** indexed search or matching that requires S2 cell intersection can miss a relevant operational intent, ISA, or subscription, depending on the concrete datastore query path and application rules.

**Not confirmed:** actual end-to-end SQL datastore query omission, remote API exploitability against a deployed service, inability of participating USS systems to discover a flight, an airborne encounter, or collision.

## Two independent fixes required

1. Validate maximum area for Circle consistently with Polygon. (Prior candidate patch does this but retains inscribed-loop undercoverage.)
2. Construct a covering of the **entire** circular region (spherical cap), not its inscribed 20-gon, to avoid false negatives.

Implement both in a coherent shared geometry function after checking radius bounds, precise max-area semantics, all RID/SCD callers, S2 cell limits and indexing costs.

## Next test

Use controlled datastore-backed SearchOperationalIntents / SearchSubscriptions or equivalent repository tests to demonstrate that the nonintersecting cell IDs yield a real false-negative query. No flight or physical hardware tests are needed.

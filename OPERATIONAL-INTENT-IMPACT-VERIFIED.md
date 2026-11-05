# Operational Intent missed-overlap: datastore and frequency validation

Baseline: `interuss/dss@e97e15eccbe87d114cf85892db6f675e05b93311`.

## Verified SCD backend false negative

- Persisted an Operational Intent with primary circle centered at (37.427636,-122.170502), radius 15,000m.
- Queried an actually overlapping 20m circle centered at (37.450505047,-122.003926497), with matching time and altitude.
- Production SCD `memstore.SearchOperationalIntents` returned **zero** matching intents.
- Reindexed the identical intent using `s2.Cap` to fully cover the circle: the same query returned **one** intent.
- GitHub Actions PASS: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/41992471834

## Confirmed SQL implementation condition

`pkg/scd/store/sqlstore/operational_intents.go` uses `scd_operations.cells && $1`, so disjoint stored/query cell arrays fail the spatial predicate. An actual running SQL backend integration test **has not** yet been performed.

## Ordinary-sized scenario sweep

Fixed 5 coordinates (Stanford, Tokyo, Zurich, London, Singapore), 6 radii for primary (1km, 3km, 5km, 10km, 15km, 20km), 1,440 bearings each. Query center always lies at 99.5% of the primary circle radius. Thus each tested secondary center is inside the primary, but the test intentionally samples near the outer rim. Each radius has 43,200 samples. All tests reuse unchanged upstream production covering code.

| Secondary radius | Missed | Samples | Cases (locations × primary radius) with any miss |
|---|---:|---:|---:|
| 20m | 121 | 43,200 | 14 / 30 |
| 50m | 41 | 43,200 | 5 / 30 |
| 100m | 3 | 43,200 | 2 / 30 |
| 200m | 0 | 43,200 | 0 / 30 |
| 500m | 0 | 43,200 | 0 / 30 |

PASS: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/41992870160

**Interpretation:** This is not a single fabricated coordinate; it repeats across cities and primary radii. Nevertheless, it is concentrated in narrow near-boundary overlap with *small* secondary circles. Rates above are conditional on choosing 99.5%-radius inner ring and should **not** be presented as live traffic or real operational error rates. The previous coarse 72-bearing sample did not hit any misses; narrow angular resolution matters.

## Impact

1. Confirmed: spatial-index false negatives; datastore-backed (in-memory repository) operational-intent search false negative.
2. Potential: missing USS discovery/coordination information when actual service areas overlap; subscription matching may also be affected.
3. Not shown: an actual CockroachDB run, HTTP end-to-end returned response, particular deployed instance, airborne collision, or any quantified safety probability.

## Engineering correction

Existing 20-vertex inscribed regular polygon systematically undercovers the requested circle; S2 Cap covering restored the demonstrated match. The separate 2,500 km² maximum-area validation bypass also exists, and a production fix should address both constraints (with radius/area validation and benchmark) rather than merely route the 20-gon into polygon covering.

## Next decision

Prioritize a focused upstream issue or patch with minimal in-memory repository reproduction, ordinary-radius sweep, and geometric fix. Before marking the change ready, add SQL-backed test and check notifications and upstream contributor guidance. Keep experimental repo public until requested otherwise.

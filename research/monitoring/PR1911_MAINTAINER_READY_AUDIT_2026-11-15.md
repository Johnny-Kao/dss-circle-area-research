# PR #1911 — Scenario cleanup and conformance review (2026-11-15)

> **Latest status (final Research gap closure):** The earlier "Residual limitations"
> section below is a historical checkpoint and is superseded by the verified
> 12/12 Research CI results in the addendum at the end of this document.
>

## Scope of this review

Review target: the **standalone Monitoring scenario and its documentation**, `oir_circle_overlap_standalone.py` and `oir_circle_overlap_standalone.md`. The historical 20-vertex polygon and baseline/fixed index comparator are **Research CI only**, never a rule for the system under test.

The scenario is a **targeted regression for one F3548-21 DSS search requirement**, NOT a certification of all ASTM F3548-21 functionality.

## Requirements traceability

| Source | Requirement / reviewer request | Evidence |
|---|---|---|
| ASTM F3548-21 DSS0005,2 and A2.2.11(2) | All relevant truly overlapping OIR references are discoverable; extra references may be returned | Single positive `Boundary overlap is discoverable` check; no negative assertion |
| Protocol F3548-21 queryOperationalIntentReferences | Query considers geographical area, altitude range and time range | Registered and query Volume4D share valid time and WGS84 altitude intervals |
| ASTM F3548-21 DSS0005,1 | Creation / deletion of OIR references works | Uses documented CRUD fragments with registered OIR ID and OVN; cleanup invoked |
| Monitoring contributor guidance | Test documentation timeless and independent of data/implementation | No historical PR, old algorithm, fixed coordinates, or old-Red assertions in scenario docs |
| Maintainer review of Monitoring PR #1911 | Dynamically select actual S2 Cell boundary within PlanningAreaResource; ensure B wholly in neighboring Cell | Level-13 actual S2 cell edge; B spherical cap containment uses *all four oriented great-circle halfspaces*, not sampled ring points |
| Maintainer review | Medium failure severity for search overlap | ⚠️ check in documented test step |
| Maintainer review | An actual adversarial boundary must be constructed, not accidental | Four independently constructed true-overlap placements, varied edge position/radius/depth, confirmed against real old and fixed APIs |

## Cleanups

1. Removed the previous reliance on externally injected witnesses **from the end-to-end verification**: CI now uses the authentic, unmodified scenario candidate.
2. Replaced sample-ring containment of the 1 m query circle with analytic spherical-cap containment in the adjacent S2 Cell. No legacy 20-vertex requirement appears in the scenario.
3. The geometry generator varies S2 boundary position and true overlap depth (0.5 and 0.1 m), then verifies actual center separation is consistent with the requested overlap within 1 mm.
4. Limited the case to at most four OIR create / search / delete cycles; all use the configured PlanningAreaResource.
5. Corrected circular Planning Area unit conversion to `radius.in_meters()`, rather than assuming radius units are already meters.
6. Ruff lint and formatter now run automatically in CI using Monitoring's E4/E7/E9/F/I/UP conventions (Python 3.14).

## Reproducible verification

- [Final CI: 7/7 successful jobs](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43678349554):
  - Discover / validate geometry: PASS.
  - Kentland rectangle: actual old DSS missing overlapping OIR (Red), fixed DSS returns it (Green).
  - Stanford rectangle: actual old DSS missing overlapping OIR (Red), fixed DSS returns it (Green).
  - Fixed DSS, Kentland concave-L area: Green.
  - Fixed DSS, Stanford concave-L area: Green.
- [Earlier no-injection 5/5 CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43677957505): old Red / fixed Green in both locations, with current contract-first multiple-case scenario.
- No CI result is counted as successful merely due to a missing fixture: the Research job explicitly rejects `Note: test_inapplicable`.
- Main scenario: `research/monitoring/oir_circle_overlap_standalone.py` (308 LOC).
- Scenario documentation: `research/monitoring/oir_circle_overlap_standalone.md` (90 lines).

## Residual limitations / release decision

1. **Full ASTM compliance is not claimed.** This tests a defined positive-search requirement and certain CRUD prerequisites, not every DSS interface or edge condition.
2. **Inapplicability semantics:** for an area without a legal fixture, the Scenario emits `test_inapplicable` and returns; Research CI rejects this as a successful regression. A general Qualifier consumer may still report a scenario with no failed checks unless it examines the note. Before upstream promotion, align this behavior with the maintainer's preferred inapplicable-test reporting conventions.
3. **Geographical scope:** API Red/Green has been demonstrated on two rectangle areas; fixed-only behavior has also passed two concave-L areas. Other areas, polar geodesics, and circular PlanningArea resources have not been tested end-to-end with this final scenario.
4. **Indexer implementation neutrality:** the API assertion is implementation-independent; however, selecting a Level-13 S2 boundary is a targeted InterUSS-specific *test data strategy*. This does not make S2 a normative ASTM obligation.
5. **Historical diagnostic guarantee:** the four dynamic test fixtures expose the old false negative in the two actual API regions tested, but not necessarily in every possible PlanningArea. Research comparator remains a separate, cheap diagnostic-strength study.

**Decision: Research implementation is contract-aligned and demonstrated end-to-end for tested settings. Staging/Upstream readiness is conditional on (2) and the maintainer's preference for handling inapplicable areas; no writes to Staging or Upstream have occurred.**

## Final Research gap closure — 2026-11-15

- Branch: `research/pr1911-final-gap-validation`
- Final verification: [12/12 successful GitHub Actions jobs](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43691554733), tested code commit `d264cea085f6d0a9bbc690a6768418681db8c119`.
- Old DSS: Kentland and Stanford produce the expected positive-overlap false negative; corrected DSS finds both.
- Corrected DSS: rectangles (Kentland, Stanford), concave-L polygons (Kentland, Stanford), circular Planning Areas (Kentland, Arctic 81°N, Antarctica 75°S), and an explicitly antimeridian-crossing circular area at 10°N / 179.99°E all pass.
- Too-small (25 m) circular Planning Area: scenario reports an **execution/configuration error** due to unavailable legal fixtures. CI verifies that this cannot be mistaken for a successful DSS conformance test.
- Fixture set: preserves the earliest four legal boundary probes to retain known regression sensitivity; when needed, adds up to two probes to verify at least two **distinct S2 Cells** and **distinct boundary-edge directions**. Selection has no 20-gon logic.
- A previously untested limitation was found in Monitoring's `Volume4D.rect_bounds` / `PlanningAreaResource.get_extents` for a circle crossing the antimeridian: an invalid wrapped `LatLngRect` leads to `AssertionError`. The Research scenario avoids this *for circular Planning Areas* by using center/radius spherical bounds and normalizing sampled longitudes. No change to the underlying Monitoring library or upstream repository was made.
- The main scenario is now ~345 physical Python lines, including comments and blank lines. Re-evaluate this maintenance cost before promoting to Staging/Upstream.

**Remaining scope boundaries:** This focused scenario validates one positive OIR-search requirement, not full ASTM F3548-21 conformance. Circles that actually enclose a geographic pole are treated as unsupported test configurations; cross-antimeridian *polygon* Planning Areas have not been validated. No fixed set of finite boundary probes can guarantee exposure of every historical implementation defect in every possible Planning Area. No Staging or Upstream writes were performed.

## Extreme-geography verification — Research CI (2026-11-15)

- [Full real-DSS CI: 15/15 jobs succeeded](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43694054578); tested code commit `6003f26ec3add71396584ce7d83b7e5599721b25`.
- North-pole-enclosing circle: center 89.97°N, 25°E, radius 5,000 m; fixed DSS search Green with multiple distinct S2 edge fixtures.
- South-pole-enclosing circle: center 89.97°S, 40°W, radius 5,000 m; fixed DSS search Green.
- Antimeridian-crossing polygon: latitude 9.985–10.015°, western/eastern vertices 179.973°E / 179.973°W (short-arc width 0.054°); fixed DSS search Green.
- Both previous old-DSS reference configurations still reproduce the false negative (old Red); corrected reference configurations pass (fixed Green).
- Other previously verified rectangular, concave-L, circle, high-latitude, dateline-circle, and too-small-configuration cases also passed in the same CI run.

**Failure and correction traced before the passing run:**

1. The pole-containing circle could not be represented by a local longitude range narrower than 360°. The scenario now samples across all longitudes while bounding latitude to [-90°, 90°], and validates each actual small OIR against the original spherical planning circle.
2. The first cross-antimeridian polygon run constructed the correct unwrapped geographic bounds but produced zero valid fixtures because Monitoring's `flatten()` subtracts longitudes directly (e.g. +179.973° versus -179.973° as ~360°, not 0.054°). A dedicated scenario-local projection now uses the shortest signed longitude delta modulo 360, while preserving the same circumference / cosine scale as the original helper. No DSS or upstream Monitor library change was made.
3. Synthetic input assertions verify the pole is strictly inside the selected 5,000 m circle and the polygon really crosses longitude ±180°. CI requires actual OIR creation/search and distinct edge and cell fixtures; configuration-only completion is not counted as success.

**Boundaries:** These successes establish the two specified extreme-geography examples, not universal applicability to all polar polygons, huge spherical caps, giant polygons with ambiguous (>180°) longitudinal spans, or all ASTM F3548-21 requirements. The scenario code is Research-only. Staging and Upstream were not changed.

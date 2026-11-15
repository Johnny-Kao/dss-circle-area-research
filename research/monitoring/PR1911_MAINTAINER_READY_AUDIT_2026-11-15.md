# PR #1911 — Scenario cleanup and conformance review (2026-11-15)

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

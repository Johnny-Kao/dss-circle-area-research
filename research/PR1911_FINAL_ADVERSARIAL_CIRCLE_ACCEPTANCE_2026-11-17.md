# PR #1911 — Final adversarial S2 circle overlap (Research acceptance)

Date: 2026-11-17 (Asia/Tokyo)
Branch: `research/pr1911-corner-adversarial-final`
Scope: **Research only**. No Staging, InterUSS Upstream, or PR conversation edits.

## Decision

**ACCEPT — Research implementation verified for Staging handoff.**

The previous 200/300 m four-edge fixture generator formed truly intersecting
circles but triggered the known indexing omission only in 19/32 or 21/32
additional geographic areas. A 37-region, 22,200-case Research study found
that **tilting the registered circle centerline about 30° relative to a true
S2 corner** creates a materially harder, deterministic scenario with no
historical polygon logic in the production test.

The *exact production-facing candidate*, not only exploratory fixtures,
was accepted by all checks listed below.

## Production fixture geometry

File: `research/monitoring/oir_circle_overlap_standalone.py` (**336 LOC**).

1. Dynamically discover actual level-13 S2 cells from the provided
   `PlanningAreaResource` (no fixed GPS coordinates).
2. For each candidate S2 **vertex**, place the 1 m circular query wholly
   inside the diagonally neighboring cell; confirm it is neither the source
   cell nor an edge-sharing cell.
3. Place the registered 300 m circular OIR's center 30° off the line from
   query center back to that vertex, entirely inside the source S2 cell.
4. Set the sphere-center separation to 300 m + 1 m - 0.1 m, and verify
   genuine spherical intersection, with about 0.1 m of positive overlap.
5. Confirm both full circles and their required margins fit the supplied
   Planning Area; select four distinct valid source-cell/corner locations.
   If the area is insufficient, return `FixtureUnavailable`, never a
   misleading DSS PASS.
6. Create one OIR per iteration, query the actual DSS API with both the
   tiny adversarial circle and a clearly contained positive-control circle,
   then delete the OIR. ASTM DSS0005,2 asserts only **positive completeness**:
   the intersecting OIR must be found, and additional false-positive
   results are allowed.

**No 20-vertex inscribed polygon, old index call, or fixed geographic
example is used by the production Scenario**. The historical and corrected
S2 coverings exist only in the independent Research oracle to measure
sensitivity. The generated query is diagonal across an S2 vertex rather
than strictly across one *edge*: this is a more challenging adjacent-cell
boundary configuration and is a point to describe explicitly in the
upstream PR review.

## Strict independent acceptance

| Gate | Result | Evidence |
| --- | --- | --- |
| Exact four-case Scenario fixture geometry in 37 locations (5 established + 32 held-out) | **37/37 valid** | [37-region CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44050903208) |
| Fixed S2 oracle correct for every actual fixture | **148/148** | [37-region CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44050903208) |
| At least one genuinely missed OIR detected by old S2 index in *every* tested region | **37/37** | [37-region CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44050903208) |
| ASTM contract, geometry, explicit query-missing fault injection, and targeted native docs check | **PASS** | [Contract CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44050637931) |
| Full Monitoring upstream `make check-hygiene`, Ruff, typing, suite registration, documentation | **PASS** | [Hygiene CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44050637891) |
| Real DSS API: old Kentland/Stanford expected RED; patched Kentland rectangle/concave-L/circle and Stanford rectangle GREEN | **6/6 SUCCESS** | [Real API CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44050637958) |

Supporting exploratory evidence:

- [True S2 corner candidate search](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44049199654) — diagonal-only line found known-bug omissions in 30/37 areas.
- [Tilted corner candidate search](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44049549104) — 22,200 true-circle cases, 37/37 areas with omissions; fixed covering correct throughout.
- The selected **fixed geometric rule** is 300 m OIR, 1 m query,
  0.1 m real overlap, 2.5 m query-center distance from S2 vertex,
  -30° centerline tilt. Across the 37 evaluated Planning Areas, the
  first four valid unique corner placements resulted in an old-index
  false-negative in every area. This is an **empirical tested-property**
  statement, not a mathematical theorem about arbitrary global geometry.

## Maintainer review alignment and limitation

The reviewer required dynamically constructing actual S2 boundary
geometry, a registered circle that truly crosses that boundary, a
wholly adjacent-cell 1m query circle, genuine positive intersection,
and normative ASTM-only assertions. The exact tested candidate meets
those geometric and conformance criteria, and demonstrates deliberate
diagnostic sensitivity without runtime selection against a historic
implementation.

**Important remaining external decision:** The Review's illustration
showed crossing an *edge* into an eastern edge-adjacent S2 cell,
whereas this final candidate crosses a *corner* into a
diagonally-adjacent cell. Both are actual adjacent-cell boundaries,
and the latter is empirically more diagnostic. The maintainer has **not
yet reviewed or approved this revised corner construction**. A claim
that the maintainer formally accepted the PR would be incorrect.

The test is not an exhaustive ASTM compliance suite. No claim is made
that any arbitrary Planning Area, even an unusually tiny or polar
polygon, supports all four fixtures, or that an older implementation
must fail in every conceivable geometry. Unavailable fixture
configurations are reported explicitly.

## Source changes and handoff

- Production Scenario: `research/monitoring/oir_circle_overlap_standalone.py`
- Timeless test documentation: `research/monitoring/oir_circle_overlap_standalone.md`
- ASTM tests: `research/monitoring/test_oir_circle_v3.py`
- 37-area exact-fixture confirmation: `research/monitoring/verify_corner_37areas.py`
- CI workflows: `.github/workflows/pr1911-corner-*.yml`

**Next authorized step:** Review the precise diff against the existing
public PR #1911 in disposable Staging, then get the user's explicit
permission before modifying any Staging or Upstream branch or posting
public comments. No additional blind geographic/radius sweeps.

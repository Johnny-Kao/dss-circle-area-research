# PR #1911 — final true-circle boundary search candidate (Research QC)

Date: 2026-11-17. Branch: `research/pr1911-final-diagnostic-selector`.
**Research only**: no Staging, Upstream, or public PR comment changes.

## Executive result

**PASS as a maintainable ASTM F3548-21 DSS0005,2 positive search test** with
demonstrated sensitivity to genuine missed-OIR defects. It does **not** claim
that an arbitrary legally configured Planning Area must reproduce the same
historical InterUSS S2 polygon indexing defect.

Source: `research/monitoring/oir_circle_overlap_standalone.py` (337 lines).
Change relative to verified v3: **one production code constant**
`OIR_RADIUS_M = 200.0 -> 300.0`; corresponding single-line scenario
documentation updated. No implementation-specific 20-gon, hard-coded GPS
test location, or invalid negative search assertion is introduced.

This retains four S2 level-13 edge orientations, a registered 300m circular
OIR, a 1m circular search query fully inside an adjacent cell, real spherical
overlap of approximately 0.1m, plus a contained-circle positive control.
Every fixture must fit in the supplied PlanningAreaResource or be explicitly
reported as unavailable, not silently accepted. Search passes only when an
actually intersecting registered OIR is present in the DSS API result; extra
references are permitted.

## Maintainer review requirements

The review at https://github.com/interuss/monitoring/pull/1911 requested
deliberate discovery of *actual* S2 cell boundaries, placement of true
circles across adjacent cells, and an ASTM-standard test scenario with
geographically independent, timeless documentation. The production test
asserts ASTM F3548-21 positive search completeness. It does not encode
historical polygon geometry in the DUT acceptance rule.

Maintainer's desired *historically adversarial* legacy polygon omission is
**observed in representative real DSS runs, not proven universal in all
possible planning areas**. This distinction should be disclosed in the PR
description/review conversation, rather than represented as vendor-specific
conformance criteria.

## Real acceptance — verified final code

1. **Original project-wide `make check-hygiene`: PASS** (native suite/docs,
   Ruff, type checks, registrations).
   https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43996514726
2. **Five-region test contract and fault injection: PASS**. In Kentland,
   Stanford, Tokyo, Zurich, Helsinki, each area produced exactly four valid
   true-circle cases: fixed S2 cap covering **4/4**, old 20-gon covering misses
   **2/4** in *each* area. A forced missing OIR correctly fails the ASTM check.
   https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43996509301
3. **Real end-to-end DSS API: 6/6 jobs PASS**. Known-bug old DSS intentionally
   RED in Stanford and Kentland; fixed DSS GREEN in Stanford rectangle and
   Kentland rectangle, concave-L, and circle Planning Areas.
   https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43996528649
4. **32 previously unseen geographic areas: PASS for portability**.
   All **32/32** produced four actual true-circle overlap cases, all
   **128/128** recovered by the corrected S2 reference oracle.
   Historical old-index omission observed in **21/32**, improved from
   original v3's **19/32**. This is **not** 32 real DSS deployments, nor a
   percentage of vendor conformance.
   https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43996521047

## Why not require old RED in every geography?

Two independent Research CI experiments showed no universal fixed geometry
for the specific old index omission, despite true-circle ASTM overlap:

- 34,275 valid true-circle candidates across the five baseline and 32 new
  areas (seven fractional edge positions, 100/200/300m radii): **11 of 32**
  new areas produced zero old-index misses with the tested geometry.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43995926745
- Varying S2-crossing depths 0.11m, 0.25m, 0.5m, 1m, 2m while holding true
  overlap about 0.1m did not fix these areas. Greater depth in fact reduced
  historic diagnostic area coverage from 26/37 at 0.11m to 4/37 at 2m.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43996212242

A vendor-independent positive search test must not be declared invalid
merely because one historically buggy implementation still happens to find
its OIR at a particular cell arrangement. **Conformance** is the API's
positive-completeness behavior on the generated real-circle cases; **bug
sensitivity** is how those samples discriminate a known defect. These are
related, not logically equivalent, acceptance criteria.

The 300m radius is a measured small improvement to diagnostic sensitivity
with no new production complexity, at the cost of requiring slightly more
Planning Area space than the original 200m radius.

## Release decision

**Research validation complete; candidate ready for authorized Staging
review.** Do not describe it as an exhaustive ASTM conformance suite or a
proof that every geographic planning area triggers an old InterUSS bug.
Do not publish or update the Upstream PR without user approval.

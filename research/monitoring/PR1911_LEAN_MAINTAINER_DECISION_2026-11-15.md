# PR #1911 — Minimal upstream candidate review (2026-11-15)

## Decision

**Preferred Research candidate:** `research/pr1911-lean-api-hybrid`,
`research/monitoring/oir_circle_overlap_standalone.py` (307 physical lines,
including whitespace and comments). This is a reduction from the 378-line
extreme-geography Research scenario, with a proven trade-off: four dynamically
selected valid S2 boundary fixtures rather than a large suite of geographic
and legacy-differential research probes.

The scope is a targeted, implementation-agnostic **ASTM F3548-21 DSS0005,2
positive search check**, not an overall certification or an S2 implementation
requirement. S2 is used solely to generate discriminating spatial inputs.

## Comparison actually tested

| Design | Python LOC | Real DSS API outcome | Decision |
|---|---:|---|---|
| Extreme-geography Research scenario | ~378 | [15/15 jobs PASS](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43694054578) | Preserve as research stress coverage |
| Relative-pattern-only compact scenario | 238 | Old Kentland Red, old Stanford unexpectedly Green; corrected cases Green | Reject for this regression goal |
| Simplified S2 scenario | 332 | [7/7 jobs PASS](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43700829772) | Valid fallback |
| Lean API + S2 geometry (preferred) | **307** | [7/7 jobs PASS](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43701500633) | Preferred |

The 307-line candidate preserves independent spherical overlap checks and the
old-Red/new-Green diagnostic behavior in **both Kentland and Stanford**.
Corrected DSS passes for both standard rectangles, the Kentland concave-L
footprint and the Kentland circular Planning Area. The CI also runs its
geometry/differential discovery job.

The actual corrected-DSS Kentland report includes **four** ordinary-contained
positive control checks and **four** boundary-overlap checks. No negative search
assertions remain.

## What belongs upstream

Five existing upstream PR #1911 file paths only:

1. `monitoring/uss_qualifier/scenarios/astm/utm/dss/oir_circle_overlap.py`
2. Adjacent `oir_circle_overlap.md` documenting the actual test steps,
   resources, ASTM requirement references and check severities
3. `monitoring/uss_qualifier/scenarios/astm/utm/dss/__init__.py` registration
4. `monitoring/uss_qualifier/suites/astm/utm/dss_probing.yaml` action
5. `monitoring/monitorlib/ids.py` next resource-type code

The focused Research CI checks that the Scenario can be inserted into the
**actual** `dss_probing.yaml`, but runs only the single-scenario suite against
the old and corrected real DSS APIs. **The complete `dss_probing` suite has
not been executed or independently approved by the maintainer.**

## Maintainer contract mapping

- No historical PR, location names, old polygon, or implementation-specific
  behavior in permanent Scenario documentation.
- Use the configured PlanningAreaResource rather than fixed GPS coordinates;
  check true geometric containment of all generated fixtures.
- Search returned a registered OIR whenever query circle and OIR overlap in
  space, altitude, time; do **not** reject extra results (ASTM permits them).
- 1 m boundary query and separate ordinary-contained positive control.
- Reuse Monitoring's CRUD fragments, fake URL convention, OIR cleanup and
  resource type registry.
- Failure to generate a fixture is a configuration/execution error, not a DSS
  conformance PASS; search check severities documented consistently.

## Scope intentionally left in Research

Full-pole circles and cross-antimeridian polygon support are verified in the
separate extreme-geography branch but are **not part of the lean candidate**.
Its general-purpose `PlanningAreaResource.get_extents()` / local projected
polygon containment can reject or mis-handle such atypical footprints.
This is an explicit reduction in portability coverage, not an unqualified
claim of universal success. Future expansion should be a separately reviewed
test if the maintainer considers these configurations necessary.

The four selected boundary fixtures are enough to reproduce the historical
miss in the two API regions tested, not guaranteed to fail every possible
legacy or third-party implementation. A compliant DSS should pass regardless
of internal indexing.

## Release boundary

Research-only. No Staging or Upstream code changes were made by this review.
Before upstream update, review the 307 LOC against the maintainer's acceptable
maintenance cost and rerun the targeted test after any staging edits.

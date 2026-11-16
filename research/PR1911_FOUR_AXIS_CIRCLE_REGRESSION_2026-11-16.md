# PR #1911 — Four-axis true-circle regression: Research handoff

Date: 2026-11-16. Repository: Johnny-Kao/dss-circle-area-research.
Branch: `research/pr1911-corner-coverage-solution`. **Research only.**
Upstream: https://github.com/interuss/monitoring/pull/1911 (not updated).
Input: `pr1911_circle_boundary_regression_final_handoff.zip` candidate (v2).

## Finding

The ZIP v2 was an ASTM-correct positive search test but returned immediately after
the first usable S2 cell edge. This missed the known old-DSS bug in the real
Kentland and Stanford environments; the old DSS passed the single test.

The known defect is an **index omission for an actually intersecting circular
OIR**. The production-facing assertion must test **true circle intersection and
presence of the OIR in the DSS search API response**, not any historical
implementation or polygon approximation.

## Fix — small deterministic orientation coverage

The production-facing Scenario `research/monitoring/oir_circle_overlap_standalone.py`
now:

1. Samples S2 level-13 cells inside the configured PlanningAreaResource using
   relative grid fractions; no site-specific coordinates are shipped.
2. Locates a valid **midpoint on each of four distinct S2 cell edge orientations**,
   trying other cells as needed. A 200 m OIR circle and a 1 m query circle have
   ~0.10 m real overlap; query circle is wholly inside the neighboring S2 cell.
3. Verifies both circle footprints fit inside the *actual* configured planning
   area; preserves the adapted valid altitude interval.
4. Creates **four OIRs, one at a time**, performs boundary-positive and ordinary
   contained-positive queries via DSS API, deletes between cases.
5. **Requires all four edge orientations**. If any are unavailable, raises
   `FixtureUnavailable` (configuration error), never silently treats partial
   orientation coverage as ASTM conformance.
6. Does **not** construct or check the historic 20-gon or infer DSS internal
   indexing. Historical S2 geometry appears **only in independent Research
   validation oracles**, not in the proposed permanent Scenario.

The query only asserts presence of the overlapping OIR; unrelated extra results
are allowed under ASTM F3548-21 DSS0005,2. No invalid negative assertions.

## Verification (known outcomes)

- Research-only full candidate search across 5 planning areas:
  Kentland 440/1200, Stanford 174/1200, Tokyo 570/1200,
  Zurich 401/1200, Helsinki 524/1200 diagnostic old-miss/fixed-hit.
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43882550200
- The **simple, exactly 4-fixture, midpoint, 200 m rule** selected independently
  (no historical model in generator) yields exactly **2 old-miss / 4 fixed-hit
  fixtures in each of Kentland, Stanford, Tokyo, Zurich, Helsinki** (10 known
  misses / 20 fixed hits across 20 actual submitted fixtures).
  Final latest positive and fault injection contract tests **5/5 PASS**,
  independent Go old/fixed S2 oracle **5/5 areas PASS**:
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43885056588
- Real DSS API, using exact 200 m four-axis scenario source:
  old `interuss/dss:v0.23.0` deliberately **RED** at Stanford and Kentland;
  repaired `Johnny-Kao/dss staging/pr-1914-review-final` **GREEN** at
  Stanford rectangle; Kentland rectangle, concave-L and circle.
  Total **6/6 acceptance jobs succeeded**, with four valid fixture notes
  verified for each environment and no execution errors:
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43884192865
- Exact upstream `make check-hygiene` passed on the same four-axis 200 m
  implementation (before the additional explicit four-orientation guard):
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43884224697
- Latest post-guard project-wide `make check-hygiene` verification:
  https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43885056476

## Acceptance boundaries and remaining upstream integration

- This is verified regression sensitivity for the **known historical index bug**,
  *not a proof of exhaustive ASTM coverage at every geographic location or for
  every vendor's implementation*. The ASTM verdict is correct for the chosen
  genuinely intersecting circles regardless of DSS internals.
- Four OIR operations are costlier than the ZIP v2's single OIR, but restore
  tested cross-orientation coverage with deterministic bounded work. Four OIRs
  also match the existing upstream PR's test-size scale.
- The earlier upstream PR's original CI is still tied to
  `interuss/dss:v0.23.0` (the known buggy version) until separately authorized
  integration. Project-native Suite registration regenerates six derived docs.
- All code, scripts, Actions, and this handoff are contained in the **Research
  repository**. No write to Staging, Upstream, or public PR comments.

# PR #1911 — boundary-only ZIP v2 evaluation (Research only)

Date: 2026-11-16. Scope: isolated Research branch `research/pr1911-circle-boundary-v2-validation` based on `research/pr1911-upstream-ci-triage`.

## Source and edit discipline

- Input: `pr1911_circle_boundary_regression_final_handoff.zip`, `pr1911_circle_boundary_regression_v2`.
- The production-facing v2 scenario and its Markdown were copied to `research/monitoring/oir_circle_overlap_standalone.py` / `.md`.
- Only four automatic Ruff code-style fixes to the scenario source (three expression layouts and one import ordering); geometry and API behavior were **not changed**. All exploration remains in Research-only scripts and workflows.
- No changes to `Johnny-Kao/monitoring` Staging, `interuss/monitoring#1911` Upstream, `interuss/dss` Upstream, or public PR comments.

## Engineering and positive ASTM contract — PASS

- Exact upstream project-wide `make check-hygiene`, project-wide Ruff, basedpyright, documentation, suite registration and v2 contract tests: **PASS**.
- CI: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43870834657
- Independent fault-injection/unit test suite: **5/5 PASS** (genuine overlap, no silently skipped tiny area, accepted extra results, failure on missing OIR, documentation contract).
- Actual patched DSS API: **GREEN** in Stanford rectangle and Kentland rectangle, concave-L, circle.
- API matrix: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43870557746

## Regression sensitivity — FAIL for two representative areas

The single fixture chosen by the ZIP's `_fixture` uses the first usable edge of the cell containing the planning-area representative point, fixed 200 m OIR radius and 0.25 m cross-edge depth.

Against **actual old DSS v0.23.0**:
- Kentland rectangle: the old DSS **returns the OIR**, `uss_qualifier` exits 0, so the Research CI job correctly fails the expected-RED acceptance check.
- Stanford rectangle: same result: **old DSS passes the candidate test** instead of triggering the historic omission.
- These failures are *missing diagnostic RED*, not execution errors or false ASTM failures.
- The independent Go S2 covering oracle of the **exact submitted fixture** confirms:
  - Kentland 0/1 old-miss/fixed-hit
  - Stanford 0/1
  - Tokyo 1/1
  - Zurich 1/1
  - Helsinki 1/1
- Oracle: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43871220485

## Research-only exploration — no new permanent implementation

1. **Four edges × three locations** of the planning reference cell per area (12 candidates):
   - Kentland 6/12, Stanford **0/12**, Tokyo 6/12, Zurich 6/12, Helsinki 6/12 diagnostic old-miss/fixed-hit.
   - CI: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43871605781
2. **Scan multiple starting S2 cells**, invoking the unchanged v2 `_fixture` on up to 49 area sample starting points:
   - Kentland 14/40, Stanford **0/39**, Tokyo 25/42, Zurich 21/42, Helsinki 19/38 diagnostic candidates.
   - CI: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43871919306
3. **5 radii × 3 crossing depths** (100, 150, 200, 250, 300 m × 0.1, 0.25, 0.5 m) with the ZIP's normal starting point and unchanged fixture algorithm:
   - **0/15** parameter combinations produce the required old-miss/fixed-hit in all five areas.
   - The most effective settings covered 3/5; Stanford and Kentland were not diagnostic at the original starting point for any of these combinations.
   - CI: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43872173098

## Decision

The ZIP's implementation-independent *ASTM positive-search assertion*, documentation approach, and small permanent scope are sound and meet the maintainer's principal conceptual requests. Its fixed one-fixture placement does **not** reliably prove the prior bug is detected and is not ready to replace the **335-line old Research candidate**, which previously achieved real old-RED/fixed-GREEN in both tested old-DSS API areas and independently 20/20 historical S2 differential fixtures across five areas.

**Recommendation:** Retain the new simpler assertion/documentation design as a promising direction; do not submit/merge the exact ZIP v2 as a regression test until a deterministic, portable fixture selection strategy consistently reproduces the known defect. Prefer independent Research diagnostics; do not embed historical `RegularLoop` or 20-gon reconstruction into permanent ASTM scenario merely to force a result. Validating both fixture construction and old-RED/fixed-GREEN remains mandatory.

No Staging or Upstream changes performed.

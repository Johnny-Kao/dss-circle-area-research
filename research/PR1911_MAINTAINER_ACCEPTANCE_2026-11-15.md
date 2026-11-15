# PR #1911 — Maintainer contract acceptance (Research, 2026-11-15)

**Candidate:** `research/pr1911-contract-acceptance` at `4913239d`. Research only; no Staging or Upstream changes.

## What was corrected

The original candidate selected the first four true-circle overlaps across adjacent S2 cells. That did not guarantee the historical diagnostic geometry. Independent testing found **Tokyo 0/4** actual selected fixtures caused an old-20-vertex S2 miss, although all four were real-circle overlaps. The source was corrected to select a fixture **only when the historical inscribed 20-vertex loop stays inside the source level-13 S2 cell**, the 1 m query circle remains wholly inside a neighboring cell, and the true circles overlap. This fixes a substantive gap in the maintainer's high-level review, rather than shrinking LOC at the expense of test validity.

The code uses the same local tangent frame as Go S2 `RegularLoop` (`getFrame`: y=Ortho(center), x=y×center), but does **not** assert that other DSS implementations use this covering. The actual DSS assertion is only the ASTM F3548-21 **positive discovery requirement**.

## Verification (actual candidate)

**Independent Go S2 oracle of the scenario's exported fixture coordinates:**
[CI run 43725920091](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43725920091)

| Area | Fixtures with old miss and fixed hit | Fixed hits |
|---|---:|---:|
| Kentland | 4/4 | 4/4 |
| Stanford | 4/4 | 4/4 |
| Tokyo | 4/4 | 4/4 |
| Zurich | 4/4 | 4/4 |
| Helsinki | 4/4 | 4/4 |

**Other acceptance checks in the same run:**

- 5/5 tests passed: true-circle positive overlap and S2 cross-cell geometry; narrow area fails fixture precondition; extra non-overlapping results are permitted; deliberately omitted overlapping OIR is recorded as a failed check; documentation satisfies contract and wording checks.
- Ruff formatter and lint passed on the **staged actual candidate**.
- Native Monitoring Scenario documentation validator passed.

**Actual DSS service API**: [CI run 43725920134](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43725920134), 7/7 jobs successful:

- Old `interuss/dss:v0.23.0`: Kentland and Stanford both **RED CONFIRMED: old DSS missed overlapping OIR** (not runner failure).
- Corrected DSS: Kentland rectangle, concave-L and circle and Stanford rectangle all **GREEN**.
- Independent fixture discovery step passed.
- The candidate was registered in a **disposable** Monitoring `dss_probing` suite during the test.

## Maintainer review alignment

- **High-level review:** Deterministically construct adversarial S2 boundary placement, with the inscribed legacy loop in the original cell and the search circle wholly inside the neighbor. Now explicitly enforced in code; separately verified against Go.
- **ASTM:** Only actual intersecting OIRs are required in results; extra references permitted. All previous invalid negative search assertions removed.
- **Timeless documentation:** No original bug narrative, specific Kentland GPS data, or implementation history in scenario Markdown.
- **Documentation clarity:** Resource permission is the client-to-DSS permission; OIRs are created one at a time; the boundary circle searches for the OIR (not vice versa); cleanup uses returned OVN.
- **Severities:** Boundary overlap warning, ordinary contained query high, matching the maintainer's requested check names.
- **Reproducible coverage:** Real API Red/Green instead of geometry-only inference.

The 17 original inline review threads are **not resolved upstream** because the source PR head is unchanged. This list is the local code/doc conformance assessment, **not a claim of maintainer approval**.

## Scope and remaining limitations

- The final original PR description is stale: it still asks to preserve invalid negative checks and claims an incomplete suite. It must be revised **with** the upstream code update, not beforehand.
- `CELL_LEVEL=13` and the 20-vertex diagnostic design target the historical InterUSS failure; the **test assertion** remains implementation-independent. A future DSS index implementation may pass without reproducing any original InterUSS miss.
- The overlap depths (0.1 and 0.5 m) remain narrow. Different Earth models or serialization can affect whether a tiny intersection is interpreted as valid. No universal cross-model ASTM compliance guarantee was established; do not claim it.
- Earlier **native complete** `dss_probing` executions reported nonzero status for *both baseline and candidate* (run 43710575288). They are not a clean full-suite green, and a precise comparison of baseline-vs-candidate failures is still needed before claiming full-suite acceptance.
- Existing targeted fixture matrix and actual DSS API acceptance are green; no new scenario-level failures found in those supported tests.

**Decision:** The Research candidate now directly satisfies the maintainer's central adversarial test requirement and passes targeted integration/contract/quality gates. Staging reduction and final PR wording review remain separate explicit steps; do not touch upstream without approval.

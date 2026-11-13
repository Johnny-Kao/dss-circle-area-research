# PR #1911 — Geometry simplification experiment (Research only)

**Decision: DO NOT PROMOTE the one-configuration shortcut.** Neither the ZIP's four-configuration search nor the reduced one-configuration search is demonstrated portable across diverse locations.

## Input

User-provided `pr1911_review_revision.zip`, particularly `test_geometry.py` and the candidate `oir_circle_overlap.py`. This is an independent, Python-only geometric emulator — not production `s2sphere` or an actual DSS service.

## Experiment A: five original representative areas

The ZIP defaults to 4 radius/crossing/query-offset tuples and 9 edge fractions. Restricting it to the single tuple `(80.0, 0.10, 1.05)` and edge fraction `(0.5,)` still produced a passing synthetic geometry in Kentland, Stanford, Tokyo, Zurich and Helsinki, with nominal overlap about 0.05 m. That small margin may be numerically fragile.

## Experiment B: expanded 200-area stress matrix

Tested 77 grid locations (latitude -75, -60, -45, -30, -15, 0, 15, 30, 45, 60, 75; longitude -170, -120, -60, 0, 60, 120, 170) plus 123 reproducible pseudorandom locations (Python `random.seed(1911)`, latitude U[-75,75], longitude U[-175,175]). Each planning-area rectangle extended 0.06 degrees north/east from the starting coordinate.

| Emulator configuration | Successful constructions | Failures |
| --- | ---: | ---: |
| Single 80 m tuple, midpoint edge fraction | 109/200 | 91/200 |
| All four ZIP tuples, midpoint edge fraction | 109/200 | 91/200 |

In this expanded experiment, the additional configurations did **not** resolve any failed area. This suggests a common failure in cell discovery, geographic extent checks, or limitations/errors in the independently implemented S2 emulator, rather than a mere lack of radius choices. Failure mechanisms have **not** been isolated.

The sampled areas are synthetic stress inputs, not guaranteed valid production `PlanningAreaResource` footprints. Accordingly, 91 failures do **not** establish that the actual Monitoring scenario fails for legitimate configured planning areas.

## What the evidence supports

1. The five ZIP examples are insufficient proof of geographic portability.
2. Reducing search combinations may be promising but is **not yet safe** without diagnosing the 91 failures and validating against genuine `s2sphere`.
3. Never conflate this geometric emulator's success with a DSS API-level Red/Green result.
4. The maintainer's core acceptance requirement remains: true OIR crosses the S2 cell boundary, legacy inscribed polygon stays on one side, and the genuinely overlapping query circle stays in a neighboring cell.

## Next mandatory gates

- Reproduce the failure matrix using real `s2sphere`, with explicit diagnosis of first failed geometric predicate and S2 face/cell boundary behavior.
- Verify practical planning-area size/shape assumptions; synthetic 0.06-degree rectangles are only stress fixtures.
- Find a minimum robust candidate strategy and rerun geographic stress cases, without hiding unsupported configurations.
- Run real pre-fix and post-fix DSS search API tests for the exact geometry.
- Run Monitoring targeted unit, qualifier and CI checks before authorizing any Staging changes.

**Boundary:** Research Repo only; no Staging or Upstream edits, no review-thread replies.

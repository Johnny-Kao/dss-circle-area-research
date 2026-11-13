# PR #1911 — failure-gate diagnosis (2026-11-14)

**Scope:** only private Research branch `research/pr1911-review-revision`. No Staging or upstream changes.

## Observations and methods

The supplied ZIP contains an independent geometric approximation in `test_geometry.py` rather than production `s2sphere`. A stand-alone gate-by-gate diagnostic was run using its functions and four original radius/offset tuples, with edge fraction set to 0.5.

| Synthetic 0.06° square | Sampled cells | Candidate checks | Legacy polygon failed containment | Valid adversarial geometry |
|---|---:|---:|---:|---:|
| lat -60°, lon 0° | 20 | 320 | 320 | 0 |
| lat 0°, lon -60° | 35 | 560 | 560 | 0 |
| Tokyo representative area | 30 | 5 (early return) | 4 | 1 |

These measurements show a specific rejection gate, **not** a DSS failure: in the failed samples, the legacy polygon has a vertex across the tested S2 cell boundary. Such cases do **not** demonstrate the old circle false-negative bug because the old polygon would have a chance to cover the neighboring cell.

One representative `(-60°, 0°)` midpoint candidate with radius 200 m and 0.75 m crossing had its most-outward legacy polygon vertex approximately 0.734 m across the boundary. At a Tokyo candidate one edge direction retained about 0.934 m inward clearance. Thus the orientation of the 20-gon relative to the S2 edge matters materially.

The emulated polygon uses an implementation of `ortho` whose equivalence with production S2 has not been established. The number of sampled cells and available edges also changes with geography; these are synthetic rectangles, not guaranteed Monitoring planning areas.

## Implications

1. Merely increasing circle configurations or sampled fractions is not a principled fix. The candidate must make the **true** circle cross the cell boundary while its **actual legacy** polygon stays inside.
2. A minimal alternative might search for a cell edge with favorable 20-gon phase rather than repeatedly testing arbitrary radii. However, it needs a margin large enough to withstand spherical approximation and API coordinate serialization.
3. Avoid near-zero margin shortcuts (for example, 80 m radius with ~5 cm overlap) as the accepted replacement until numeric robustness is measured.
4. Compare the **actual old DSS S2 covering cells** and the **fixed DSS S2 cap covering cells**, not only containment of synthetic 20-gon vertices. That is a strict Red/Green prerequisite.

## Next research experiments

- Use production `s2sphere` and compare legacy polygon vertices/coverer against the emulator.
- Make diagnostics report signed polygon-to-edge clearance and genuine-query overlap in meters.
- Test candidate search against real `PlanningAreaResource` bounds, including small areas and antimeridian crossings.
- Select a minimal but reliable candidate generator; then run old/fixed DSS HTTP search behavior.
- Only if both Red/Green and CI pass consider moving code to Staging.

`s2sphere` is not installed in the current sandbox and package installation failed due to unavailable network/DNS. No claim of production S2 validation or real API integration is made.

Diagnostic reproduction helper: `research/monitoring/pr1911_failure_diagnostics.py`. Place next to `test_geometry.py` extracted from the ZIP to run it.

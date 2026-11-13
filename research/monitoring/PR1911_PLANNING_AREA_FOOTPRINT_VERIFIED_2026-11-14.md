# PR #1911 — Real PlanningArea footprint containment validation

Date: 2026-11-14 JST. Scope: Research only. No Staging or upstream changes.

## Contract confirmed from upstream Monitoring

`PlanningAreaResource.get_extents()` returns a **bounding rectangle** of `resolved_volume4d_with_times(None, None).rect_bounds`. It does not guarantee that the original Planning Area is rectangular. The underlying `resolved_volume4d_with_times(None, None).volume` is a `Volume3D` carrying either `outline_polygon` or `outline_circle`.

Therefore, checking only lat/lng minimum and maximum may select circles outside a concave polygon. This was a genuine fixture-construction issue in the Research candidate; it does **not** establish a production DSS bug.

## Production-path candidate change

`research/monitoring/oir_circle_overlap_review.py` now checks that the **entire** generated registered OIR and boundary query circle are contained in the actual Planning Area:

- Polygon: project using Monitoring's `flatten` around the Planning Area center, build a Shapely polygon, inward-buffer by circle radius plus a 1 m margin, and require the center to be within the eroded polygon. This handles a concave footprint and prevents a circle protruding over polygon edges, within local projection assumptions.
- Circular Planning Area: compare great-circle center distance plus candidate radius plus 1 m tolerance against the configured area circle radius.
- Preserve original bounding-box fast rejection and existing S2 boundary construction / four candidate configurations.
- No DSS search semantics changed. It remains a positive ASTM F3548-21 discovery requirement; the S2/20-gon generator remains a targeted regression fixture for the original circular-covering defect.

## Actual DSS Red / Green integration tests

GitHub Actions [43502372218](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43502372218): **20/20 jobs SUCCESS**.

Matrix:
- Regions: Kentland, Tokyo, Zurich, Helsinki, Stanford.
- Shapes: rectangular footprint and six-vertex **concave L-shaped** footprint with the *same bounding rectangle* (removes the north-east quadrant).
- DSS variants: legacy `interuss/dss:v0.23.0` and fixed source `Johnny-Kao/dss@staging/pr-1914-review-final`.
- All ten legacy jobs verified the missing-overlap assertion (intentional Red); all ten fixed jobs passed the actual qualifier API searches (Green).
- No scenario execution errors accepted as Red.

## Direct footprint contract unit tests

GitHub Actions [43503764603](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43503764603): **4 tests PASS** using the actual reviewed `OIRCircleOverlap._circle_inside_volume` helper and actual Monitoring and S2 dependencies:

1. A point inside the bounding box but in the excluded concave corner is rejected.
2. A circle fully inside the polygon is accepted.
3. A circle with its **center inside**, but footprint beyond an edge, is rejected.
4. A circular Planning Area accepts contained circle and rejects a partially protruding circle.

The first footprint CI attempt [43503610788](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43503610788) failed due to the standalone test script's `PYTHONPATH`, not due to the geometry; the test harness was corrected and re-run successfully.

## Limitations and review questions

- `flatten` is Monitoring's local planar projection, not a globally exact spherical polygon containment test. Longitude antimeridian crossings, polar/high-latitude regions, and unusually large footprints remain outside demonstrated coverage. The 1 m margin does not prove a universal numerical bound.
- The 20/20 integration matrix demonstrates five moderately sized Planning Areas, not all legal small/complex shapes. An unsupported tiny or narrow area can still fail to construct an adversarial fixture and should be classified as a precondition / inapplicability issue rather than a DSS defect.
- S2 level 13 and the 20-sided legacy polygon are still implementation-specific adversarial fixture choices. The assertion itself is ASTM-conformant.
- The best follow-on work is to define explicit Planning Area footprint size/geometry preconditions and avoid adding further geometry abstraction unless a concrete test demonstrates need.

**Status:** Verified Research candidate, not yet proposed for Staging or upstream promotion. User approval required for any Staging/Upstream change.

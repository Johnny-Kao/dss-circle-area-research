# PR #1911 — Maintainer-aligned cleanup and minimum-pattern experiment

Date: 2026-11-14 JST. Research only; no staging/upstream changes.

## Changes under test

- Revised `research/monitoring/oir_circle_overlap.md` to present timeless ASTM F3548-21 search requirements, remove InterUSS bug history and invalid negative checks, and describe exactly one generated OIR, a boundary overlap and contained-circle positive search.
- Removed unused negative-search branches from `research/monitoring/oir_circle_overlap_review.py`.
- Changed the boundary check description severity to warning in Markdown, consistent with the maintainer's review.
- The independent scenario formatting, import, ID uniqueness and documentation validation workflow succeeded in Actions run [43499366934](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43499366934).
- Full five-region old/fixed DSS Red/Green matrix on cleanup candidate succeeded **10/10** in Actions run [43499366798](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43499366798).

## Simpler geometry experiment

Replaced the four radius/crossing/query-offset combinations with only `(200.0, 0.75, 1.25)`; left edge and geographic sampling unchanged.

Actions run [43500273647](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43500273647):
- Kentland, Tokyo, Helsinki: old and fixed jobs passed (6/6).
- Zurich, Stanford: both jobs failed (4/4).
- Report artifacts show explicit `ValueError: Could not construct S2 adversarial geometry inside planning area` in both failed regions, not DSS search false negatives.
- Thus **a single 200 m circle configuration does not meet our demonstrated portability threshold**. The failure arises in fixture construction, prior to the relevant API assertion.

The four proven configurations were restored in commit `c220f39`. Its regression CI was automatically triggered (run [43500856378](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43500856378)); final status requires checking.

## Remaining limitations

- This is a generic ASTM **search assertion** with a targeted InterUSS S2/20-gon regression fixture generator, not a guarantee of fixture construction in every valid planning area or every DSS implementation.
- The current geometry validates against the planning area's lat/lng bounding **box**, not a potentially nonrectangular planning-area polygon; a general planning-area contract requires full containment or an explicit rectangular-area precondition.
- Need stronger overlap margins and coverage for small areas, high latitudes and longitude seam before claiming universal portability.
- Avoid removing additional geometry configurations without Red/Green evidence across all supported fixtures.

No upstream or staging edits.

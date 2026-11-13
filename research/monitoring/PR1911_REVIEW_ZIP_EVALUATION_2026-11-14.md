# Monitoring PR #1911 — maintainer review and ZIP evaluation (2026-11-14)

Status: **Research only**. This branch does not modify Monitoring staging or upstream.

## Maintainer's requirements (BenjaminPelletier, 2026-11-12)

- The regression must deliberately construct a challenging level-13 S2 cell-boundary geometry, not rely on accidental overlaps from arbitrary planning areas.
- Specifically: the true circular OIR crosses an S2 cell edge, its old 20-vertex inscribed polygon remains in the original cell, and a 1 m query circle is wholly in the neighboring cell while genuinely overlapping the OIR.
- Remove assertions that disjoint spatial, altitude, or temporal queries must exclude an OIR: ASTM F3548-21 DSS0005,2 requires no false negatives, but permits extra results from grid-cell indexing.
- Keep the ordinary contained-circle positive sanity check and OIR creation/deletion checks.
- Scenario documentation should be timeless, vendor-neutral, and avoid research anecdotes, Kentland and PR history.
- Clarify DSS client authorization, test step wording and check severity (boundary check warning).

Source: https://github.com/interuss/monitoring/pull/1911

## User-provided ZIP reviewed

Source ZIP: pr1911_review_revision.zip, containing replacement `oir_circle_overlap.py`, `oir_circle_overlap.md`, `test_geometry.py`, `validate_revision.py`, patch and TEST_RESULTS.md.

The ZIP implements a candidate-cell discovery process using level-13 S2 cell edges, edge fractions, and several radius/offset configurations. It checks candidate geometry and returns one passing case. It removes negative search assertions and aligns the Markdown scenario with the review.

## Independent checks in this session

- Extracted and inspected ZIP source and supporting tests.
- Ran the standalone `test_geometry.py`: **PASS** for its five synthetic example bounding boxes (Kentland, Stanford, Tokyo, Zurich and Helsinki).
- Ran ZIP's `validate_revision.py` directly after extraction: **FAIL** because it hard-codes `/mnt/data/pr1911_revision/...`. Replacing that path with a path relative to `__file__` made the validation **PASS**. The shipped harness still requires that portability fix.
- Python `py_compile` of the replacement scenario **PASS** in this session. No full Monitoring checkout/dependencies or DSS service available in this sandbox. No genuine end-to-end Red/Green or integration result is established for this ZIP.
- Independent harness reimplements S2 geometry rather than importing production `s2sphere`, so agreement with actual cell selection/coverer still needs verification.

## Remaining validation gates

1. Adapt ZIP validation script to repo-relative paths and execute.
2. Check actual `s2sphere` API compatibility, cell-edge normals, neighbor interpretation, true covering behavior and planning-area bounds.
3. Confirm the chosen candidate fails on legacy DSS and passes on fixed DSS at the API level (not merely on a standalone geometry emulator).
4. Run targeted Monitoring tests, static checks, documentation and suite registration, followed by the relevant dss_probing integration suite.
5. Evaluate if repeated search loops and candidate discovery add undue cost or maintenance burden; consider a simpler deterministic geometry construction if equivalent.
6. Only after research evidence passes, compare minimal proposed code diff against the existing PR and seek explicit approval before any staging/upstream update.

## Important distinction

The ZIP's `TEST_RESULTS.md` reports other checks as passed in its author's environment. Those claims were **not independently reproduced here**. No branch of `interuss/monitoring` or `Johnny-Kao/monitoring` was modified.

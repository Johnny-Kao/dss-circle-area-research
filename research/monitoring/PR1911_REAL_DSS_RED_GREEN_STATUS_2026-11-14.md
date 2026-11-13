# PR #1911 — Real DSS Red/Green CI attempt (2026-11-14 JST)

**Status: BLOCKED — no valid Red/Green result.**

## Implemented in Research only

- `research/monitoring/oir_circle_overlap_review.py`: S2 level-13 cell-boundary candidate generator, true-circle overlap and 20-gon containment checks, positive OIR search assertions. It drops invalid negative assertions.
- `.github/workflows/pr1911-review-red-green.yml`: runs the **same** reviewed scenario through `uss_qualifier` against two actual DSS images: old `interuss/dss:v0.23.0` and locally built fixed `Johnny-Kao/dss@staging/pr-1914-review-final`.
- Red acceptance requires nonzero qualifier status **and** exact missing-OIR assertion, excluding scenario execution errors. Green acceptance requires successful qualifier status and no missing-OIR assertion. Failure to start infrastructure is neither Red nor Green.
- The existing testing environment is inherited from Research's `pr1914-monitoring-old-red.yml` (DSS API stack and self-contained test config).

## Execution attempt and blocker

Action run [43490250692](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43490250692) was triggered by the workflow commit. Both matrix jobs (`integration (old)` and `integration (fixed)`) concluded **failure**, but the GitHub connector returned empty job steps and job log retrieval failed with GitHub's `BlobNotFound` (HTTP 404). Thus there is **no evidence that either DSS server ran or that the scenario reached the API**. Treat this as CI execution/instrumentation blocked, **not** a legitimate Red/Green result.

The original workflow specified `ubuntu-26.04`, which was changed to `ubuntu-24.04` in commit `495686b9` to remove one potential runner compatibility issue. The revised workflow's run/result must still be checked; do not infer success.

## Mandatory remaining steps

1. Confirm GitHub Actions actually schedules both jobs on an available runner and surfaces step logs.
2. Fix environment/setup errors, if any, with direct job logs (not guesses).
3. Verify the scenario imports `s2sphere` and matches actual Go DSS legacy polygon/coverer behavior.
4. Capture the actual OIR ID and two DSS search responses; confirm **old misses** and **fixed returns** the same geometrically valid overlap.
5. Archive raw log/artifacts and only then label Red/Green verified.

No changes to Staging or upstream. No unverified test success claims.

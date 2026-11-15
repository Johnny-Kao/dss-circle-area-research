# PR #1911 — Complete native DSS probing acceptance (2026-11-15)

## Verdict

**Candidate-only functional regression: PASS.**
**Complete suite, strict zero-failures validation: NOT PASS (three unchanged mock-environment failures).**

The full native `suites.astm.utm.dss_probing` was executed on the same
corrected DSS build and Monitoring revision in two isolated GitHub Actions
runners: once without this scenario (baseline) and once with
`OIRCircleOverlap` integrated into the real Suite file (candidate).
This was NOT a single-scenario smoke test.

- [Full-suite baseline/candidate GitHub Actions run](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43710575288)
- Research branch: `research/pr1911-full-dss-probing-acceptance`
- Source Scenario: `research/monitoring/oir_circle_overlap_standalone.py`
- Same corrected DSS staging reference checked out read-only:
  `Johnny-Kao/dss@staging/pr-1914-review-final`
- Monitoring tested from `interuss/monitoring@main` in disposable CI checkout

## Structured uss_qualifier report comparison

| Metric | Baseline | Candidate |
| --- | ---: | ---: |
| Native Suite actions | 22 | 23 |
| Executed Scenario reports | 21 | 22 |
| Passed Checks | 1,903 | **1,920** |
| Failed Checks | 3 | **3** |
| Scenario execution errors | 0 | **0** |
| Skipped actions | 1 | **1** |
| Command exit status | 2 | 2 |

**All 21 existing executed Scenario types had identical pass-check counts
in the two reports.** The only additional passed checks were the 17 from
`OIRCircleOverlap`. The newly integrated scenario had exactly zero failures
and no execution errors.

## New Scenario evidence

- 4 successful `Create operational intent reference query succeeds` checks
- 4 successful `Boundary overlap is discoverable` checks (ASTM F3548-21 DSS0005,2)
- 4 successful `Ordinary contained circle discovers OIR` checks (ASTM F3548-21 DSS0005,2)
- 4 successful `Delete operational intent reference query succeeds` checks
- 1 successful setup cleanup/query check
- 0 failed checks, 0 execution errors
- Valid boundary fixtures were actually constructed, OIRs created and deleted,
  and true API search responses recorded

## Baseline environmental exceptions (unchanged)

All 3 Medium failed checks came from the existing
`DSSInteroperability` test step `Test environment requirements`,
check `DSS instance is publicly addressable`, because container-based
mock services resolve to private Docker addresses (172.18.0.x). These are
environment prerequisites, not a new OIR search regression.
The same three failure names and summaries occurred in both runs.

One original `DatastoreAccess` action was skipped in both runs because
`dss_datastore_cluster` was not provided in the local mock configuration.
This is **not** a completed validation of DatastoreAccess.

The two GitHub Actions matrix jobs are marked **Failure** because both
`uss_qualifier` commands returned exit code 2 for those same existing
Medium checks. This is not misrepresented as an all-green full-suite run.
The full reports, raw logs, and execution artifacts were retained on the run.

## Scope / release decision

The maintainer-requested positive-overlap scenario works inside the original
native `dss_probing` suite, adding no failures to the 21 existing executed
scenarios. **Targeted integration acceptance is satisfied**; a formal
zero-failure whole-suite acceptance requires a suitable publicly addressable
test environment (and the optional datastore resource for coverage).
No baseline exceptions should be silently suppressed as a substitute.

Only Research repository files and disposable CI checkouts were changed.
Neither Staging nor Upstream was modified.

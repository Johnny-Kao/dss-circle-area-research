# PR #1911 — Upstream review and failing CI triage (Research only)

**Date:** 2026-11-16 JST  
**Upstream PR:** https://github.com/interuss/monitoring/pull/1911  
**Original PR head:** `70a4267c96b5ed769c2aac1dc293027aeeb14a98` (3 commits, 5 changed files).  
**Original PR base:** `55728f7d95c5aaf96f08f515815c4080fe18dd56`.  
**Research branch:** `research/pr1911-upstream-ci-triage`, based on fully verified 334-line candidate `research/pr1911-final-simplification`.  
**Safety:** All code and workflow edits confined to Research. No updates to fork staging branch `Johnny-Kao/monitoring`, upstream PR, or PR comments.

## Original PR checks: 20 passed, 4 failed

Upstream CI run: https://github.com/interuss/monitoring/actions/runs/43131812299

1. **Repository hygiene** — https://github.com/interuss/monitoring/actions/runs/43131812299/job/130997900394  
   Exact failure: Ruff `I001` import-order violation in `monitoring/uss_qualifier/scenarios/astm/utm/dss/__init__.py`; appended `from .oir_circle_overlap import ...` appeared at the end rather than alphabetically before `oir_explicit_sub_handling`. The **full original CI gate stopped at Ruff**, so its later checks did not run.

2. **dss_probing** — https://github.com/interuss/monitoring/actions/runs/43131812299/job/130997900822  
   Exact test failure: `Boundary overlap is discoverable` returned `returned_ids=[]` although registered OIR was expected. The environment sets `DSS_IMAGE=interuss/dss:v0.23.0`, which intentionally exercises the old broken circle-cover behavior. `stop_fast: true` upgrades the original High-severity check to Critical and terminates the suite early. This is **not** a container startup failure and not proof that the corrected DSS fails.

3. **f3548_self_contained** — https://github.com/interuss/monitoring/actions/runs/43131812299/job/130997900868  
   Same old-image circular overlap false negative, **plus** DSS0300 `DSS instance is publicly addressable` checks due to Docker RFC1918/private IPs. Two distinct causes; neither should be hidden by weakening or deleting the positive overlap assertion.

4. **utm_implementation_us** — https://github.com/interuss/monitoring/actions/runs/43131812299/job/130997900923  
   Same `Boundary overlap is discoverable` OIR omission under default `interuss/dss:v0.23.0`, with `stop_fast` aborting subsequent checks.

Default image is pinned in `build/dev/run_locally.sh` (`DSS_IMAGE=${DSS_IMAGE:-interuss/dss:v0.23.0}`); it is not automatically replaced by merged upstream DSS source code.

## Maintainer review coverage

**17 original inline review threads plus one high-level review**; they remain unresolved **in the upstream PR**, because no PR code or comments were modified.

Research 334-line candidate alignment:

- Inline #1–6: Scenario documentation is timeless, does not mention Kentland, five research locations, the originating bug or InterUSS's indexing internals. Unclear and historical wording removed.
- Inline #7–8: Client-to-DSS authorization and PlanningAreaResource described as required.
- Inline #9–11 and #15–16: accepted OIRs are created **one at a time**; a 1 m boundary query searches for and must discover the registered OIR. The Research version uses **100–300 m primary radii** and **up to four fixtures**, not the original suggested 700–1,100 m; this is an intentional, functionally verified reparameterization, not literal adoption of the suggested numbers.
- Inline #12: boundary-overlap finding documented as ⚠️ Medium rather than 🛑 High.
- Inline #13: invalid negative assertions (searches outside time/altitude/space must not return an OIR) **removed** because ASTM F3548-21 permits false positives; positive true-overlap requirement retained.
- Inline #14: ordinary contained **query circle discovers** the OIR; no misleading claim that the circle itself is discovered.
- Inline #17: remove unnecessary `test-owned` language; cleanup/deletion via returned OVN.
- High-level: explicitly construct adversarial S2 cell boundary; require entire query circle in neighbor and historical inscribed polygon in original cell, so circle intersections are diagnostic. Independent Go S2 oracle: **20/20 actual chosen fixtures distinguish old miss vs fixed hit**.

These are local conformance findings, **not maintainer acceptance**.

## Research changes made after reading upstream logs

- New helper: `research/monitoring/stage_oir_circle_for_upstream_ci.py` stages **all five original PR file categories** into a disposable Monitoring checkout and inserts registry import at the correct alphabetical position; native `dss_probing` suite and resource ID marker are registered.
- New CI workflow: `.github/workflows/pr1911-upstream-ci-readiness.yml` pins the original PR base and runs whole-repository Ruff format/lint, project-native docs, real native suite registration, import and 5 behavioral tests.
- Initial CI: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43734361331 proved **whole-repo Ruff PASS** but exposed six **missing generated Suite Markdown** updates, previously hidden by the original upstream Ruff failure.
- Corrected CI: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43734548583 **PASSED** after running the official `format_test_suite_docs.sh` in the disposable upstream checkout. It generated these six derivative documents:
  - `monitoring/uss_qualifier/suites/astm/utm/dss_probing.md`
  - `monitoring/uss_qualifier/suites/astm/utm/f3548_21.md`
  - `monitoring/uss_qualifier/suites/uspace/required_services.md`
  - `monitoring/uss_qualifier/suites/uspace/flight_auth.md`
  - `monitoring/uss_qualifier/suites/interuss/dss/all_tests.md`
  - `monitoring/uss_qualifier/suites/faa/uft/message_signing.md`
- Corrected CI confirmed: `1021 files already formatted`, entire-repository `ruff check` PASS, generated native Suite docs pass project-native `make lint`, scenario import and dss_probing registration PASS, and 5/5 ASTM positive/fault injection tests PASS.
- Full `make check-hygiene` has also been added to the CI gate, for follow-up validation of exact upstream repository procedures.

## Important distinctions / constraints

1. **Source test correct vs upstream CI green**: Research actual DSS API matrix https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43732530726 previously established 2 expected RED on `interuss/dss:v0.23.0`, and 4 GREEN on repaired DSS. **An upstream CI still pinned to v0.23.0 cannot pass a legitimate regression test for the fixed bug**; the long-term upstream integration must update/override the image only when a repaired version is available.
2. **Do not silence the test** by adding skip/xfail against v0.23.0 in production-facing ASTM Scenario or by weakening the positive assertion. That would defeat the regression goal.
3. **Generated docs must be part of the eventual authorized staging diff** if upstream requires them; they must not be regenerated solely inside CI and omitted from the PR. They were generated only inside disposable CI so far.
4. **DSS0300**: Do not delete addressability checks. The full Suite's separate Docker private-address issue can be recorded as an accepted local test finding if the official configuration supports it, without changing ASTM standard assertions.
5. Prior full-suite baseline and candidate comparison used **repaired DSS** and had the same DSS0300 private-IP failures. It does not explain the original PR's old-image OIR failures.
6. No staging/upstream PR mutation has been authorized.

**Review outcome:** The Research candidate meets the maintainer's main contract/diagnostic requirements and now has a complete local CI integration reproduction. The original upstream PR remains stale and **its four failing checks remain unresolved there** until a separately authorized staging/upstream update; the primary external blocker is CI using the unrepaired `interuss/dss:v0.23.0`.

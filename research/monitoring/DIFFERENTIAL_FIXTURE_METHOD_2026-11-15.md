# Differential Fixture Discovery — reusable engineering method

This is a research-only procedure for finding **high-value, reproducible regression tests**. Do not confuse it with the behavior that a production implementation must expose.

## 1. Separate the three things being measured

| Layer | Question | Oracle |
|---|---|---|
| Semantic contract | What output is correct for this input? | Independent mathematical/specification check |
| Boundary candidate | Does the input exercise a relevant implementation boundary? | Input properties, not the known faulty code |
| Diagnostic strength | Can this input distinguish defective from correct behavior? | Differential execution of baseline and fixed versions, or purposeful mutants |

For ASTM F3548-21 DSS search, the semantic requirement is: if the true circular footprints overlap in space, altitude and time, the registered OIR must be returned. False positives are allowed. Neither the 20-vertex approximation nor a particular S2 covering is a normative behavior of the DSS API.

## 2. Discover and certify

1. Generate many **valid, independent candidates** at real spatial cell edges and vertices. Use true circle geometry to enforce positive overlap and ensure the full query circle lies in a neighboring cell. Never derive candidates from an old implementation's regular polygon.
2. Run each candidate through a **cheap version oracle**. Here, an isolated Go program compares the old `RegularLoop(...,20)` covering with the corrected `CapFromCenterAngle` covering. The historical algorithm appears **only in this research adapter**. Other projects must provide their own baseline/fixed or mutation adapter.
3. Select a candidate only when the baseline demonstrates a miss and the fixed implementation does not. Keep the full list of candidates and results, not just the first successful example.
4. Reproduce the selected input against the **real production API** using the original and corrected versions. An S2-only difference is a *hypothesis* until this step passes.
5. Save the minimal witness and its independent semantic explanation. Production contract tests should assert the semantic behavior, not the historical defect's internal intermediate values.

**Failure taxonomy:** no valid input in the supplied area; valid input but no differential witness found; cheap-oracle difference but API does not reproduce; actual semantic contract violation; fixed-version regression. Never label an unsuccessful search as proof that a defect is absent.

## 3. Evidence, 2026-11-15

- [Differential discovery CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43672044807): PASS. 11 geographic centers, 160 edge + 200 vertex candidates each, **3,960 total**. Corrected cap indexing succeeds on all 3,960 synthetic checks. **Nine of eleven** locations have at least one candidate demonstrating the known baseline indexing miss. Equator and Sydney have **no witness in this bounded search**, not proof of impossibility.
- [Real DSS HTTP API CI](https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/43671962975): PASS, **4/4**. Independently selected Kentland and Stanford witnesses both produce old Red and fixed Green. The API scenario still asserts only that a genuinely overlapping OIR must be returned.
- Candidate geometry generator: `differential_fixture_candidates.py` (no historical 20-gon fixture rules).
- Historical cover comparison is isolated in `differential_s2_cover_oracle.go` (research only).
- Generic witness selection: `select_differential_witnesses.py`.
- The selected cases are preserved in `differential_witnesses.json`. `inject_differential_witness.py` modifies **only the disposable Monitoring checkout** for integration research.

## 4. Applying this to another project

Replace the three domain-specific adapters: (a) semantic oracle, (b) valid boundary-input generator, (c) baseline-vs-fixed or mutant evaluator. Keep the same selection criterion, failure taxonomy, reproducibility manifest and end-to-end recheck.

For unknown future defects, differential testing against the known old bug is not enough: add **property-based / metamorphic tests and mutation testing**. Each property must state a correctness invariant and a mutation that its test demonstrably detects. Version-differential witnesses establish coverage of *known* failure classes, not unknown bugs or all possible input spaces.

## 5. Delivery boundary

Research scripts, historical bug adapters and static geographic witness manifests do **not** automatically belong in the portable upstream Monitoring scenario. The production scenario must remain contract-first, respect its PlanningAreaResource, and make an unavailable diagnostic fixture visible rather than silently accepting a generic pass. Do not promote changes into Staging or Upstream without the user's authorization.

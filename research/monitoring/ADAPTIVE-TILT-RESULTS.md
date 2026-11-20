# Adaptive S2 corner tilt research — 2026-11-21

## Scope
Research-only evaluation for interuss/monitoring PR #1911. No upstream changes. All runs use the unchanged historical DSS baseline e97e15eccbe87d114cf85892db6f675e05b93311 and production GeoCircle.CalculateCovering as the legacy oracle.

## Method
37 deterministic global reference centers (lat=-65+(17*i mod 131), lng=-170+(73*i mod 341), i=0..36), with a representative local 0.026° latitude by 0.060° longitude sampling envelope. This is an independent sample, **not** Benjamin's 2002 planning areas and **not** a complete reproduction of the Monitoring PlanningAreaResource bounds checks.

Fixed control: original -30°.
Two-angle control: -30° and +30° in both orders, stopping at 4 fixtures.
Adaptive: for each encountered S2 vertex, enumerate integer angles -85°..+85° and keep those for which the 300.9 m offset circle center belongs to the source level-13 S2 cell. Select the midpoint of successive quartiles of the feasible angle list, depending on fixture index 0..3. Require the 1 m query circle to fit in the diagonal S2 cell and a geodesically verified ~0.1 m real-circle overlap. Stop at 4 fixtures.

The adaptive algorithm uses **only geometric feasibility**, not the legacy covering result, to choose angles. The legacy covering is examined after selection. Every adaptive candidate must also have intersecting S2 Cap coverings as a positive geometric control. This is a geometric green oracle, **not a running patched DSS HTTP API**.

## GC results
Run: https://github.com/Johnny-Kao/dss-circle-area-research/actions/runs/44788441851

- Fixed -30°: 35/37 regions had at least one legacy missed overlap.
- Fixed +30°: 36/37.
- Mixed [-30°, +30°] with a strict four-fixture limit: 37/37.
- Mixed [+30°, -30°] with a strict four-fixture limit: 37/37.
- Adaptive feasible-angle quartiles with a strict four-fixture limit: 37/37 valid fixtures and 37/37 with legacy missed overlap; 37/37 also passed the corrected S2 Cap overlap control.
- All tested combinations ran successfully under GitHub Actions.

## Interpretation and limits
This supports using a small deterministic geometry-derived angle selector without fixed ±30° constants. It does **not** establish global mathematical optimality, actual deployed error probability, or a general guarantee across all locations. The candidate selection currently samples in 1° increments, and corners remain visited in numerical S2 cell-ID order. The research proxy does not check the full shape or margins of user-provided PlanningAreaResource, so tests may overestimate fixture availability in unusually small or shaped planning areas.

## Next validation before upstream
Port adaptive candidate selection into a disposable Monitoring research staging branch (not the upstream PR). Reuse true planning area constraints and existing exception semantics, test old-DSS Red and patched-DSS Green through actual HTTP APIs for multiple areas, run full Monitoring suite, and quantify candidate-generation runtime. Only then consider whether complexity is justified versus the maintainer-approved ±30° alternative.

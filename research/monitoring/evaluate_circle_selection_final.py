"""Research-only score vendor-independent fixed selection rules, never runtime oracle."""
import json
import sys
from collections import defaultdict
from pathlib import Path

cases = [json.loads(x) for x in Path(sys.argv[1]).read_text().splitlines()]
results = [json.loads(x) for x in Path(sys.argv[2]).read_text().splitlines()]
assert len(cases) == len(results)
by_area = defaultdict(list)
for a, b in zip(cases, results):
    assert a["name"] == b["name"] and a["caseIndex"] == b["caseIndex"]
    assert b["fixed_hit"], (a, b)
    by_area[a["name"]].append((a, b))


def select(area, priorities, max_cases=4):
    selected = []
    used = set()
    for target_fraction, target_radius in priorities:
        for a, b in area:
            key = a["edge"]
            if key in used:
                continue
            if a["fraction"] != target_fraction or a["radius"] != target_radius:
                continue
            # Candidate selection uses only input geometry, not the oracle.
            selected.append((a, b))
            used.add(key)
            break
        if len(selected) == max_cases:
            break
    return selected


def select_unique_edges(area, fraction_order, radius_order):
    selected = []
    for edge in range(4):
        for frac, radius in ((f, r) for f in fraction_order for r in radius_order):
            options = [x for x in area if x[0]["edge"] == edge
                       and x[0]["fraction"] == frac
                       and x[0]["radius"] == radius]
            if options:
                selected.append(options[0])
                break
    return selected


schemes = {
    "midpoint200": ([.5], [200.]),
    "quarter200": ([.25], [200.]),
    "threequarter200": ([.75], [200.]),
    "third200": ([.375], [200.]),
    "fiveeighth200": ([.625], [200.]),
    "midpoint300": ([.5], [300.]),
    "quarter300": ([.25], [300.]),
    "midpoint100": ([.5], [100.]),
    "nonmid200": ([.375, .625, .25, .75, .5], [200.]),
    "third100": ([.375, .625, .25, .75, .5], [100.]),
    "third300": ([.375, .625, .25, .75, .5], [300.]),
    "diverse": ([.375, .625, .25, .75, .5, .125, .875], [200., 100., 300.]),
    "alt-mid": ([.25, .5, .75, .125, .875], [200., 300., 100.]),
}
print("AREAS", len(by_area), "CASES", len(cases))
any_miss_area = 0
for name, cases_for_area in sorted(by_area.items()):
    old_miss = [x for x in cases_for_area if not x[1]["old_hit"]]
    any_miss_area += bool(old_miss)
    print("AREA", name, "valid", len(cases_for_area),
          "diagnostic", len(old_miss),
          "first", [(x[0]["caseIndex"], x[0]["edge"], x[0]["fraction"],
                     x[0]["radius"]) for x in old_miss[:2]])
print("ALL_CANDIDATE_DIAGNOSTIC_AREAS", any_miss_area, "/", len(by_area))
for name, (fractions, radii) in schemes.items():
    counts = []
    for area, rows in sorted(by_area.items()):
        selected = select_unique_edges(rows, fractions, radii)
        misses = sum(not b["old_hit"] for a,b in selected)
        counts.append((area, len(selected), misses))
    print("SCHEME", name,
          "areas_hit", sum(x[2] > 0 for x in counts), "/", len(counts),
          "areas_complete", sum(x[1] == 4 for x in counts), "/", len(counts),
          "total_old_misses", sum(x[2] for x in counts), "/", sum(x[1] for x in counts),
          "uncovered", [x[0] for x in counts if x[2]==0])

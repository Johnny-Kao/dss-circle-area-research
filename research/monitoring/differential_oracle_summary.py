"""Summarize research differential oracle results and assert coverage."""

import collections
import json
import sys

stats = collections.defaultdict(lambda: [0, 0, 0])
first = {}
for line in sys.stdin:
    x = json.loads(line)
    a = stats[x["name"]]
    a[0] += 1
    a[1] += int(not x["old_hit"] and x["fixed_hit"])
    a[2] += int(x["fixed_hit"])
    if not x["old_hit"] and x["fixed_hit"] and x["name"] not in first:
        first[x["name"]] = x
for name, (all_count, mutant_detected, fixed_green) in stats.items():
    first_hit = first.get(name)
    print(
        f"{name:13s} generated={all_count} oldRed={mutant_detected} newGreen={fixed_green} first_idx={first_hit['caseIndex'] if first_hit else '-'} first_R={first_hit['radius'] if first_hit else '-'}"
    )
print("ALL LOCATIONS DIAGNOSTIC", len(first) == len(stats))
required = set(sys.argv[1:])
missing = sorted(required - set(first))
if missing:
    print(f"Required diagnostic witnesses not found: {missing}", file=sys.stderr)
    sys.exit(1)

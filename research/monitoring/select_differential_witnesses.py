"""Select semantic-valid fixtures that distinguish baseline from fixed behavior.

Input is JSONL from an arbitrary version-oracle adapter. Candidates are
generated without baseline implementation details; oracle results must provide
name, primary, query, radius, old_hit, fixed_hit.
"""

import argparse
import json
import sys
from pathlib import Path


def select_witnesses(lines):
    selected = {}
    counts = {}
    for line in lines:
        record = json.loads(line)
        name = record["name"]
        counts[name] = counts.get(name, 0) + 1
        if not record["old_hit"] and record["fixed_hit"] and name not in selected:
            selected[name] = {
                "radius": record["radius"],
                "primary": record["primary"],
                "query": record["query"],
                "caseIndex": record["caseIndex"],
            }
    return selected, counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", help="Version-oracle results JSONL")
    p.add_argument("output", help="Chosen witnesses, keyed by location")
    p.add_argument("--require", nargs="*", default=[])
    args = p.parse_args()
    with open(args.input, encoding="utf-8") as source:
        chosen, counts = select_witnesses(source)
    Path(args.output).write_text(json.dumps(chosen, indent=2, sort_keys=True) + "\n")
    for name in sorted(counts):
        item = chosen.get(name)
        print(
            f"{name}: {counts[name]} examined, "
            f"{'witness=' + str(item['caseIndex']) if item else 'NO_WITNESS'}"
        )
    missing = sorted(set(args.require) - set(chosen))
    if missing:
        print(f"Missing required witnesses: {missing}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

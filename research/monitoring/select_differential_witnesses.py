"""Select semantic-valid fixtures that distinguish baseline from fixed behavior.

Input is JSONL from an arbitrary version-oracle adapter. Candidates are
generated without baseline implementation details; oracle results must provide
name, caseIndex, and the domain-specific witness payload. Verdicts may use
baseline_correct/candidate_correct, or the legacy old_hit/fixed_hit adapter.
"""

import argparse
import json
import sys
from pathlib import Path


def is_diagnostic(record):
    """Baseline violates the independent contract, fixed candidate satisfies it."""
    if "baseline_correct" in record and "candidate_correct" in record:
        return not record["baseline_correct"] and record["candidate_correct"]
    # Backward-compatible schema for the circular OIR search adapter.
    return not record["old_hit"] and record["fixed_hit"]


def select_witnesses(lines):
    selected = {}
    counts = {}
    for line in lines:
        record = json.loads(line)
        name = record["name"]
        counts[name] = counts.get(name, 0) + 1
        if is_diagnostic(record) and name not in selected:
            verdict_fields = {
                "baseline_correct",
                "candidate_correct",
                "old_hit",
                "fixed_hit",
            }
            selected[name] = {
                key: value for key, value in record.items() if key not in verdict_fields
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

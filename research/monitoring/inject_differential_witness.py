"""Inject a previously validated witness into a disposable Monitoring checkout.

RESEARCH CI ONLY. This does not modify the upstream candidate or source repo.
The actual API assertion continues to depend solely on true geometric overlap.
"""

import argparse
import json
from pathlib import Path


def inject(scenario_path, witness_path, region):
    data = json.loads(Path(witness_path).read_text())
    witness = data[region]
    a = witness["primary"]
    b = witness["query"]
    radius = witness["radius"]
    # Independent center-distance check: false positives are not used as witnesses.
    import math

    ar, br = math.radians(a[0]), math.radians(b[0])
    delta_lng = math.radians(b[1] - a[1])
    hav = (
        math.sin((br - ar) / 2) ** 2
        + math.cos(ar) * math.cos(br) * math.sin(delta_lng / 2) ** 2
    )
    d = 2 * 6371010.0 * math.asin(min(1.0, math.sqrt(hav)))
    overlap = radius + 1.0 - d
    assert overlap > 0.01, f"invalid true-circle witness: {overlap}"
    marker = "    def _fixture(self, volume):\n"
    path = Path(scenario_path)
    src = path.read_text()
    assert src.count(marker) == 1
    snippet = (
        f'        self.record_note("fixture_constructed", "Research differential '
        f'witness {region}: overlap={overlap:.3f} m")\n'
        f"        return (Circle.from_meters({a[0]!r}, {a[1]!r}, {radius!r}),\n"
        f"                Circle.from_meters({b[0]!r}, {b[1]!r}, 1.0))\n"
    )
    path.write_text(src.replace(marker, marker + snippet, 1))
    print(f"Injected research witness for {region}: R={radius}, overlap={overlap:.3f}m")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("scenario_path")
    p.add_argument("witness_path")
    p.add_argument("region")
    args = p.parse_args()
    inject(args.scenario_path, args.witness_path, args.region)

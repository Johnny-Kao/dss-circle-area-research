"""Apply the two requested test-file moves to a checked-out DSS PR tree.

Runs only in GitHub Actions research runner. Does not touch upstream.
"""
from pathlib import Path

root = Path("dss")
changes = [
    ("pkg/models/circle_covering_test.go", "pkg/models/geo_test.go"),
    ("pkg/scd/store/memstore/circle_covering_test.go", "pkg/scd/store/memstore/operational_intents_test.go"),
]
for source, target in changes:
    src, dst = root / source, root / target
    original = src.read_text()
    # Preserve test functions/helpers, not a second package/import block.
    marker = "\nfunc "
    if source.startswith("pkg/models/"):
        marker = "\n// Independent great-circle"
        text = dst.read_text().replace('import (\n', 'import (\n\t"math"\n', 1)
    else:
        text = dst.read_text()
    assert marker in original, source
    code = original[original.index(marker):]
    assert code not in text, "Test already moved: " + target
    dst.write_text(text.rstrip() + "\n\n" + code.lstrip("\n"))
    src.unlink()
    print(source, "->", target)

"""Stage PR #1911 into a disposable upstream Monitoring checkout.

Research CI helper. Never writes to Staging or to the upstream PR.
The output must be used to run project-native hygiene and suite checks.
"""

from pathlib import Path


def main() -> None:
    source = Path("research/research/monitoring")
    root = Path("monitoring/monitoring")
    scenario_dir = root / "uss_qualifier/scenarios/astm/utm/dss"
    registry = scenario_dir / "__init__.py"
    suite = root / "uss_qualifier/suites/astm/utm/dss_probing.yaml"
    ids = root / "monitorlib/ids.py"

    for extension in ("py", "md"):
        destination = scenario_dir / f"oir_circle_overlap.{extension}"
        assert not destination.exists(), f"Already present: {destination}"
        destination.write_text(
            (source / f"oir_circle_overlap_standalone.{extension}").read_text()
        )

    import_line = "from .oir_circle_overlap import OIRCircleOverlap as OIRCircleOverlap\n"
    before = "from .oir_explicit_sub_handling import OIRExplicitSubHandling as OIRExplicitSubHandling\n"
    content = registry.read_text()
    assert content.count(before) == 1 and import_line not in content
    registry.write_text(content.replace(before, import_line + before, 1))

    ids_content = ids.read_text()
    assert ids_content.count("# Next code: 406") == 1
    ids.write_text(ids_content.replace("# Next code: 406", "# Next code: 408", 1))

    suite_content = suite.read_text()
    anchor = (
        "  - test_scenario:\n"
        "      scenario_type: scenarios.astm.utm.dss.OIRValidation\n"
    )
    assert suite_content.count(anchor) == 1
    scenario_type = "scenarios.astm.utm.dss.OIRCircleOverlap"
    assert scenario_type not in suite_content
    entry = (
        "  - test_scenario:\n"
        f"      scenario_type: {scenario_type}\n"
        "      resources:\n"
        "        dss: dss\n"
        "        id_generator: id_generator\n"
        "        planning_area: planning_area\n"
    )
    suite.write_text(suite_content.replace(anchor, entry + anchor, 1))
    assert suite.read_text().count(scenario_type) == 1
    print("Staged five PR files: scenario .py/.md, sorted registry, IDs, native Suite.")


if __name__ == "__main__":
    main()

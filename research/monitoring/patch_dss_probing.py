"""Add the circle regression to Monitoring's existing DSS probing suite (research only)."""

from pathlib import Path


def register_in_dss_probing(monitoring_root: Path) -> None:
    suite = monitoring_root / "monitoring/uss_qualifier/suites/astm/utm/dss_probing.yaml"
    text = suite.read_text()
    scenario = "scenarios.astm.utm.dss.OIRCircleOverlap"
    if scenario in text:
        return
    entry = """
  - test_scenario:
      scenario_type: scenarios.astm.utm.dss.OIRCircleOverlap
      resources:
        dss: dss
        id_generator: id_generator
        planning_area: planning_area
"""
    assert "  planning_area: resources.PlanningAreaResource" in text
    assert "  id_generator: resources.interuss.IDGeneratorResource" in text
    assert "  dss: resources.astm.f3548.v21.DSSInstanceResource" in text
    suite.write_text(text.rstrip() + "\n" + entry)


if __name__ == "__main__":
    import sys

    register_in_dss_probing(Path(sys.argv[1]))

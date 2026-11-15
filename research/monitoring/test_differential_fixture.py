"""Regression tests for generic differential witness selection and S2 geometry."""

import json
import unittest

from differential_fixture_candidates import candidates, cid, corner_candidates, ring
from select_differential_witnesses import select_witnesses


class FixtureDiscoveryTests(unittest.TestCase):
    def test_edge_candidate_has_true_overlap_and_disjoint_centers(self):
        c = next(candidates("Stanford", 37.43, -122.17, max_results=1))
        self.assertGreater(c["overlap"], 0)
        self.assertNotEqual(c["primaryCell"], c["queryCell"])
        import s2sphere as s

        center = s.LatLng.from_degrees(*c["query"]).to_point()
        self.assertTrue(all(cid(p).id() == c["queryCell"] for p in ring(center, 1.0)))

    def test_corner_candidate_is_diagonal(self):
        import s2sphere as s

        c = next(corner_candidates("Arctic", 81, -5, max_results=1))
        a = s.CellId(c["primaryCell"])
        self.assertNotIn(s.CellId(c["queryCell"]), a.get_edge_neighbors())
        self.assertGreater(c["overlap"], 0)

    def test_selection_requires_old_red_and_fixed_green(self):
        entries = [
            {
                "name": "test",
                "radius": 100,
                "primary": [1, 2],
                "query": [3, 4],
                "caseIndex": 0,
                "old_hit": True,
                "fixed_hit": True,
            },
            {
                "name": "test",
                "radius": 100,
                "primary": [1, 2],
                "query": [3, 4],
                "caseIndex": 1,
                "old_hit": False,
                "fixed_hit": False,
            },
            {
                "name": "test",
                "radius": 200,
                "primary": [1, 2],
                "query": [3, 4],
                "caseIndex": 2,
                "old_hit": False,
                "fixed_hit": True,
            },
        ]
        selected, counts = select_witnesses(json.dumps(c) + "\n" for c in entries)
        self.assertEqual(counts["test"], 3)
        self.assertEqual(selected["test"]["caseIndex"], 2)

    def test_generic_oracle_and_domain_payload(self):
        cases = [
            {
                "name": "other_project",
                "caseIndex": 7,
                "input": {"size": 4096, "boundary": 4095},
                "baseline_correct": False,
                "candidate_correct": True,
            }
        ]
        selected, _ = select_witnesses(json.dumps(c) + "\n" for c in cases)
        self.assertEqual(selected["other_project"]["input"]["boundary"], 4095)
        self.assertNotIn("baseline_correct", selected["other_project"])

    def test_no_witness_is_not_treated_as_pass(self):
        cases = [{"name": "test", "old_hit": True, "fixed_hit": True}]
        selected, counts = select_witnesses(json.dumps(c) + "\n" for c in cases)
        self.assertEqual(counts["test"], 1)
        self.assertNotIn("test", selected)


if __name__ == "__main__":
    unittest.main()

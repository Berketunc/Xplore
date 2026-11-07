import unittest

from backend.ranking import select_candidates


class RankingTests(unittest.TestCase):
    def select(self, values, costs=None):
        runs = [{"candidate_id": cid, "status": "completed" if value is not None else "failed", "deformation_pct": value}
                for cid, value in values.items()]
        return select_candidates(runs, list(values), 20, costs or {})

    def test_no_candidate_passes(self):
        result = self.select({"flexible": 30, "firm": 21}, {"flexible": 1, "firm": 3})
        self.assertEqual(result["qualifying_candidate_ids"], [])
        self.assertIsNone(result["recommended_candidate_id"])

    def test_ties_use_deformation_then_stable_id(self):
        result = self.select({"c": 10, "b": 8, "a": 8}, {"a": 2, "b": 2, "c": 2})
        self.assertEqual(result["cost_ranking"], ["a", "b", "c"])

    def test_incomplete_costs_do_not_invent_winner(self):
        result = self.select({"flexible": 10, "firm": 5}, {"flexible": 2})
        self.assertIsNone(result["recommended_candidate_id"])
        self.assertEqual(result["missing_cost_candidate_ids"], ["firm"])

    def test_failure_makes_selection_provisional(self):
        result = self.select({"flexible": None, "firm": 20}, {"firm": 5})
        self.assertTrue(result["provisional"])
        self.assertEqual(result["recommended_candidate_id"], "firm")

    def test_nonfinite_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            self.select({"firm": float("nan")})

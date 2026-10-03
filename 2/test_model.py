import ast
import json
import unittest
from pathlib import Path

from kfrage_model.kfrage_sim import (
    Simulation, Scenario, compare_with_observed, classify_path, state_payload
)
from kfrage_model.example_custom_personality import AlwaysWaitWuest


ROOT = Path(__file__).parent


class KFrageModelTests(unittest.TestCase):
    def test_baseline_is_reproducible(self):
        a = Simulation(Scenario()).run()
        b = Simulation(Scenario()).run()
        self.assertEqual([e.action for e in a.events], [e.action for e in b.events])

    def test_baseline_calibration_is_post_run(self):
        state = Simulation(Scenario()).run()
        self.assertEqual(classify_path(state), "historical_like_sequence")
        self.assertEqual(compare_with_observed(state)["calibration_result"], "PASS_natural_sequence_reproduced")

    def test_observed_comparator_not_referenced_by_decisions(self):
        tree = ast.parse((ROOT / "kfrage_sim.py").read_text(encoding="utf-8"))
        offenders = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name not in {
                "compare_with_observed", "state_payload"
            }:
                names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
                if "OBSERVED_COMPARATOR" in names:
                    offenders.append(node.name)
        self.assertEqual(offenders, [])

    def test_assumptions_are_valid_json(self):
        data = json.loads((ROOT / "assumptions.json").read_text(encoding="utf-8"))
        self.assertIn("unknown_black_boxes", data)
        self.assertTrue(data["anti_leakage"]["decision_access"].startswith("No decision"))

    def test_one_personality_can_be_replaced_without_changing_environment(self):
        baseline = Simulation(Scenario()).run()
        replaced = Simulation(Scenario(), policies={"Wuest": AlwaysWaitWuest()}).run()
        self.assertEqual(baseline.actions["Merz"], replaced.actions["Merz"])
        self.assertEqual(replaced.actions["Wuest"], "remain_ambiguous")
        wuest_event = next(e for e in replaced.events if e.node == "Wuest")
        self.assertEqual(wuest_event.policy_id, "example_always_wait_wuest")
        self.assertNotEqual(classify_path(baseline), classify_path(replaced))

    def test_environment_is_declarative_and_complete(self):
        env = json.loads((ROOT / "environment.json").read_text(encoding="utf-8"))
        self.assertEqual(set(env["actors"]), {"Merz", "Wuest", "Soeder"})
        self.assertEqual(len(env["timeline"]), 9)
        self.assertTrue(all(step["handler"] in env["allowed_timeline_handlers"] for step in env["timeline"]))

    def test_blind_payload_excludes_observed_comparator(self):
        state = Simulation(Scenario()).run()
        payload = state_payload(Scenario(), state, blind=True)
        self.assertTrue(payload["blind_mode"])
        self.assertNotIn("observed_comparison", payload)
        self.assertNotIn("historical", payload["path_class"].lower())


if __name__ == "__main__":
    unittest.main()

import unittest

from kfrage_model.example_layered_v3 import build
from kfrage_model.scenario_reporting import ScenarioReportCompiler, ScenarioReportingPolicy


class ScenarioReportingTests(unittest.TestCase):
    def test_full_scenario_emits_both_mandatory_charts(self):
        result = build().run("demo")
        report = result["scenario_report"]
        self.assertTrue(report["valid"])
        self.assertEqual(report["used_persona_cards"], ["Merz"])
        self.assertEqual(
            {row["step"] for row in report["pss_pressure_series"]},
            {0, 1},
        )
        self.assertEqual(
            {row["step"] for row in report["polling_series"]},
            {0, 1},
        )
        self.assertIn("<svg", report["charts"]["pss_pressure_svg"])
        self.assertIn("<svg", report["charts"]["polling_svg"])

    def test_missing_polling_fails_loudly_by_default(self):
        compiler = ScenarioReportCompiler(
            {"Merz": {"pressure": 0.500}},
            ScenarioReportingPolicy(),
        )
        trace = [{
            "node": "n",
            "decision_maker": "Merz",
            "actors_used": ["Merz"],
            "all_actor_pss_after": {"Merz": {"pressure": 0.600}},
        }]
        with self.assertRaisesRegex(RuntimeError, "missing realtime polling series"):
            compiler.compile(trace, ())


if __name__ == "__main__":
    unittest.main()

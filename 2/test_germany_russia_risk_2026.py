import unittest

from kfrage_model.scenarios.germany_russia_risk_2026.run_scenario import (
    SNAPSHOT,
    STATES,
    policy_vector,
    run_decisions,
    run_ensemble,
    run_party_round,
    simulate_path,
)


class GermanyRussiaRiskTests(unittest.TestCase):
    def test_snapshot_starts_in_hybrid_confrontation_not_war(self):
        self.assertEqual(SNAPSHOT["state"], "S1_HYBRID_CONFRONTATION")
        self.assertFalse(SNAPSHOT["direct_hostilities"])
        self.assertGreater(SNAPSHOT["nuclear_rhetoric"], SNAPSHOT["nuclear_posture"])

    def test_same_seed_reproduces_full_contingent_path(self):
        decisions, _, _ = run_decisions(20261001, False)
        policy = policy_vector(decisions)
        self.assertEqual(simulate_path(87, policy), simulate_path(87, policy))

    def test_no_timestep_can_skip_a_conflict_level(self):
        decisions, _, _ = run_decisions(20261001, False)
        policy = policy_vector(decisions)
        for seed in range(100):
            for row in simulate_path(seed, policy)["trace"]:
                self.assertLessEqual(abs(STATES.index(row["to"]) - STATES.index(row["from"])), 1)

    def test_decision_space_contains_contingent_s2_and_s3_nodes(self):
        decisions, _, _ = run_decisions(20261001, False)
        self.assertGreaterEqual(len(decisions), 9)
        self.assertIn("S2", {row["stage"] for row in decisions})
        self.assertIn("S3", {row["stage"] for row in decisions})
        self.assertTrue(any(any(value != 0 for value in row["state_utility_adjustments"].values())
                            for row in decisions if row["stage"] == "S3"))

    def test_ensemble_is_not_forced_to_war_and_retains_deescalation_routes(self):
        decisions, _, _ = run_decisions(20261001, False)
        result = run_ensemble(20261001, policy_vector(decisions), 1000)
        final = result["checkpoints"]["52"]
        self.assertGreater(final["S0_GREY_ZONE"], 0)
        self.assertGreater(final["S1_HYBRID_CONFRONTATION"], 0)
        self.assertLess(final["S4_NATO_RUSSIA_CONVENTIONAL_CONFLICT"], 1)

    def test_afd_is_party_collective_not_persona(self):
        parties = run_party_round()
        self.assertEqual(parties["AFD"]["party_id"], "AFD")
        self.assertTrue(parties["AFD"]["rule"].startswith("party common interests"))
        self.assertEqual(parties["AFD"]["chosen_action"], "challenge_attribution_dialogue_first")

    def test_arcana_audit_is_replayable_and_conflict_aware(self):
        _, _, arcana = run_decisions(20261001, True)
        self.assertEqual(len(arcana["audits"]), 9)
        self.assertTrue(all(row["reading"]["seed"] is not None for row in arcana["audits"]))
        self.assertTrue(all("conflict_interaction" in row for row in arcana["audits"]))


if __name__ == "__main__":
    unittest.main()

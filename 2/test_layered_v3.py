import unittest
import json
from dataclasses import replace
from pathlib import Path

from kfrage_model.action_perception import ActionPerceptionFilter
from kfrage_model.action_repertoire import ActionRepertoireFilter
from kfrage_model.arcana import ArcanaConfig, ArcanaService
from kfrage_model.checks.constitutional import build_gg_check_engine
from kfrage_model.checks.context import BundestagState, CheckContext
from kfrage_model.free_agent_game import FreeAgentGame, FreeAgentNode, WorldAction
from kfrage_model.information_filter import AccessRule, InformationFilter
from kfrage_model.institutional_logic import InstitutionalLogic
from kfrage_model.interaction.intents import Intent
from kfrage_model.persona_v2 import ActionOption, FreeAgentDecisionEngine, WorldEvent
from kfrage_model.party_interest import PartyInterestEngine
from kfrage_model.political_agency import AgencyHorizon
from kfrage_model.political_state import PoliticalAction, PoliticalState, StateVariable
from kfrage_model.rationality_evaluation import ActorRationalityProfile, RationalityEvaluator
from kfrage_model.scenario_reporting import ScenarioReportingPolicy
from kfrage_model.simulation_orchestrator import (
    LayeredConfiguration,
    LayeredSimulationOrchestrator,
    SimulationNodeV3,
    V3FeatureFlags,
)
from kfrage_model.system_feedback import SystemFeedbackAssessor


ROOT = Path(__file__).parent
CARDS = ROOT / "personality_cards_2026" / "cards_pss.json"
ENV = ROOT / "environments" / "2026-07-31" / "environment.json"
RATIONALITY = ROOT / "personality_cards_2026" / "rationality_profiles_v3.json"
PARTIES = ROOT / "party_profiles_2026" / "party_interest_profiles.json"


def build_components():
    state = PoliticalState(
        {
            "formal_power_view": StateVariable("formal_power_view", 90),
            "world_stability": StateVariable("world_stability", 50),
        },
        {},
        {},
    )
    info = InformationFilter({
        "Merz": {
            "formal_power_view": AccessRule(0.95),
            "world_stability": AccessRule(0.80),
        }
    })
    actions = (
        WorldAction(
            PoliticalAction(
                "stabilize",
                {"immediate": {"world_stability": 5}, "medium": {}, "long": {}},
                feasibility=0.85,
            ),
            ActionOption(
                "stabilize",
                value_impacts={"strategic_direction": 0.5, "unity": 0.5},
                required_resources={"formal_power": 0.7},
                upside=0.4,
                downside=0.05,
                identity_tags=("strategic_direction", "authority"),
                control_domains=("direction",),
                instrumental_impacts={"government_capacity": 0.7},
                substantive_impacts={"democratic_deliberation": -0.1},
                necessity_frame_alignment=0.8,
                autonomy_impacts={"backbenchers": -0.2},
            ),
        ),
        WorldAction(
            PoliticalAction(
                "wait",
                {"immediate": {"world_stability": 0}, "medium": {}, "long": {}},
                feasibility=0.95,
            ),
            ActionOption(
                "wait",
                value_impacts={"strategic_direction": -0.4, "unity": 0.1},
                required_resources={"formal_power": 0.2},
                upside=0.1,
                downside=0.1,
                identity_tags=("avoid",),
                instrumental_impacts={"government_capacity": -0.1},
                substantive_impacts={"democratic_deliberation": 0.1},
            ),
        ),
    )
    return state, info, actions


class LayeredV3Tests(unittest.TestCase):
    def test_arcana_conflict_is_optional_and_fully_exposed_in_scenario_report(self):
        state, info, actions = build_components()
        result = LayeredSimulationOrchestrator(
            state,
            {"n": SimulationNodeV3("n", "Merz", actions, conflict_actor="Soeder")},
            FreeAgentDecisionEngine.from_json(CARDS),
            info,
            {"Merz": {"formal_power": "variable:formal_power_view"}},
            LayeredConfiguration.from_environment_json(ENV),
            arcana=ArcanaService(ArcanaConfig(enabled=True, master_seed=1773)),
            reporting_policy=ScenarioReportingPolicy.diagnostics_only(),
        ).run("n")
        turn = result["trace"][0]
        self.assertTrue(turn["arcana"]["enabled"])
        self.assertIn("advice_process", turn["arcana"]["reading"])
        self.assertIn(
            "counterparty_reading",
            turn["arcana"]["conflict_interaction"],
        )
        self.assertIn(
            "primary_pss_mediation",
            turn["arcana"]["conflict_interaction"]["interaction"],
        )
        self.assertEqual(
            result["scenario_report"]["used_persona_cards"],
            ["Merz", "Soeder"],
        )
        compact = result["scenario_report"]["arcana_report_trace"]
        self.assertEqual(compact["schema_version"], "arcana-report-trace-1.0")
        self.assertEqual(compact["nodes"][0]["actor"], "Merz")
        self.assertIn("conflict", compact["nodes"][0])
        self.assertNotIn("arcana_audit", result["scenario_report"])
        # The forensic trace remains available independently of presentation data.
        self.assertEqual(turn["arcana"]["status"], "RUN")

    def test_environment_v3_configuration_loads_in_shadow_mode(self):
        config = LayeredConfiguration.from_environment_json(ENV, RATIONALITY)
        self.assertTrue(config.flags.shadow_mode)
        self.assertEqual(config.logic.logic_id, "federal_union_government_2026_shadow_v1")
        self.assertIn("Merz", config.agency.values)
        self.assertIn("Frei", config.rationality_profiles)

    def test_rationality_profiles_are_separate_normalized_three_decimal_inputs(self):
        payload = json.loads(RATIONALITY.read_text(encoding="utf-8"))
        for actor, row in payload["actors"].items():
            values = [value for key, value in row.items() if key.endswith("_weight")]
            self.assertAlmostEqual(sum(values), 1.0, places=3, msg=actor)
            self.assertTrue(all(0.0 <= value <= 1.0 and round(value, 3) == value for value in values))

    def test_shadow_mode_preserves_v2_choice_and_world_result(self):
        state_v2, info_v2, actions_v2 = build_components()
        state_v3, info_v3, actions_v3 = build_components()
        old = FreeAgentGame(
            state_v2,
            {"n": FreeAgentNode("n", "Merz", actions_v2)},
            FreeAgentDecisionEngine.from_json(CARDS),
            info_v2,
            {"Merz": {"formal_power": "variable:formal_power_view"}},
        ).run("n")
        config = LayeredConfiguration.from_environment_json(ENV)
        new = LayeredSimulationOrchestrator(
            state_v3,
            {"n": SimulationNodeV3("n", "Merz", actions_v3)},
            FreeAgentDecisionEngine.from_json(CARDS),
            info_v3,
            {"Merz": {"formal_power": "variable:formal_power_view"}},
            config,
            reporting_policy=ScenarioReportingPolicy.diagnostics_only(),
        ).run("n")
        self.assertEqual(old["trace"][0]["chosen_action"], new["trace"][0]["chosen_action"])
        self.assertEqual(old["world_state"], new["world_state"])
        self.assertEqual(new["trace"][0]["decision_source"], "persona_v2_compatibility")

    def test_resource_shortfall_is_visible_but_not_removed_from_role_menu(self):
        config = LayeredConfiguration.from_environment_json(ENV)
        action = ActionOption("large_move", required_resources={"formal_power": 0.9})
        rows = ActionRepertoireFilter(config.matrix).apply("Merz", (action,), {"formal_power": 0.4})
        self.assertEqual(rows["large_move"].role_status, "AVAILABLE")
        self.assertLess(rows["large_move"].resource_coverage, 1.0)
        self.assertIn("insufficient_resources_soft_constraint", rows["large_move"].reasons)

    def test_logic_narrows_perception_without_selecting_action(self):
        config = LayeredConfiguration.from_environment_json(ENV)
        action = ActionOption(
            "deviate",
            institutional_deviation=0.9,
            organizational_carrier_requirements={"organization_base": 0.8},
        )
        repertoire = ActionRepertoireFilter(config.matrix).apply(
            "Merz", (action,), {"organization_base": 0.3}
        )
        perceived = ActionPerceptionFilter().apply(
            (action,),
            repertoire,
            config.logic,
            AgencyHorizon(0.2, 0.2, 0.2, 0.3),
            {"organization_base": 0.3},
            0.8,
        )["deviate"]
        self.assertEqual(perceived.perceived_status, "NOT_SERIOUSLY_CONSIDERED")
        self.assertIn("low_organizational_carrier", perceived.reasons)

    def test_dual_evaluation_preserves_rationality_conflict(self):
        engine = FreeAgentDecisionEngine.from_json(CARDS)
        action = ActionOption(
            "discipline",
            instrumental_impacts={"passage": 0.9},
            substantive_impacts={"deliberation": -0.7},
        )
        persona = engine.score("Frei", action, {}, {}, ())
        row = RationalityEvaluator().evaluate(
            action, persona, ActorRationalityProfile(), perceived_feasibility=0.9
        )
        self.assertGreater(row.instrumental_score, row.substantive_score)
        self.assertGreater(row.rationality_conflict, 0.5)

    def test_system_feedback_is_separate_from_operational_success(self):
        engine = FreeAgentDecisionEngine.from_json(CARDS)
        action = ActionOption(
            "absorb_critique",
            instrumental_impacts={"capacity": 0.8},
            substantive_impacts={"deliberation": -0.5},
            necessity_frame_alignment=0.9,
            institutional_deviation=0.0,
            autonomy_impacts={"leadership": 0.2, "backbenchers": -0.4},
        )
        persona = engine.score("Frei", action, {}, {}, ())
        evaluation = RationalityEvaluator().evaluate(
            action, persona, ActorRationalityProfile(), perceived_feasibility=0.9
        )
        feedback = SystemFeedbackAssessor().assess(
            action, evaluation, InstitutionalLogic.neutral(), 0.9
        )
        self.assertEqual(feedback.reproduction_type, "ADAPTIVE_REPRODUCTION")
        self.assertGreater(feedback.logic_reinforcement, 0.0)

    def test_system_mutation_flag_does_not_implicitly_activate_v3_choice(self):
        flags = V3FeatureFlags(system_feedback_mutates_world=True)
        self.assertFalse(flags.choice_active)
        self.assertFalse(flags.shadow_mode)

    def test_choice_channels_can_be_activated_independently(self):
        logic_only = V3FeatureFlags(institutional_logic_affects_choice=True)
        agency_only = V3FeatureFlags(agency_horizon_affects_choice=True)
        self.assertTrue(logic_only.choice_active)
        self.assertTrue(agency_only.choice_active)
        self.assertFalse(logic_only.agency_horizon_affects_choice)
        self.assertFalse(agency_only.institutional_logic_affects_choice)

    def test_party_interest_overlay_is_visible_and_opt_in(self):
        state, info, actions = build_components()
        enriched = tuple(
            WorldAction(
                item.world,
                replace(
                    item.choice,
                    party_interest_impacts={
                        "government_capacity": 0.800 if item.world.key == "stabilize" else -0.600,
                        "organizational_unity": 0.600 if item.world.key == "stabilize" else -0.300,
                    },
                    party_strategy_impacts={
                        "government_stability": 0.800 if item.world.key == "stabilize" else -0.600,
                    },
                ),
            )
            for item in actions
        )
        base = LayeredConfiguration.from_environment_json(ENV, RATIONALITY)
        config = LayeredConfiguration(
            base.matrix,
            base.logic,
            base.agency,
            base.rationality_profiles,
            V3FeatureFlags(party_interest_affects_choice=True),
        )
        result = LayeredSimulationOrchestrator(
            state,
            {"n": SimulationNodeV3("n", "Merz", enriched)},
            FreeAgentDecisionEngine.from_json(CARDS),
            info,
            {"Merz": {"formal_power": "variable:formal_power_view"}},
            config,
            party_interests=PartyInterestEngine.from_json(PARTIES),
            actor_party_map={"Merz": "CDU_CSU"},
            party_overlay_weights={"Merz": 0.300},
            reporting_policy=ScenarioReportingPolicy.diagnostics_only(),
        ).run("n")
        trace = result["trace"][0]
        self.assertEqual(trace["decision_source"], "layered_v3_party_overlay")
        self.assertEqual(trace["party_interest_layer"]["party_id"], "CDU_CSU")
        self.assertEqual(trace["party_interest_layer"]["overlay_weight"], 0.300)
        self.assertIsNotNone(trace["action_evaluations"]["stabilize"]["party_interest"])

    def test_strategic_forecast_rebuilds_future_actors_perceived_menu(self):
        base = LayeredConfiguration.from_environment_json(ENV, RATIONALITY)
        config = LayeredConfiguration(
            base.matrix,
            base.logic,
            base.agency,
            base.rationality_profiles,
            V3FeatureFlags(strategic_response_uses_perceived_menu=True),
        )
        state = PoliticalState({"x": StateVariable("x", 50)}, {}, {})
        opening = WorldAction(
            PoliticalAction("open", {"immediate": {"x": 1}, "medium": {}, "long": {}}, next_node="reply"),
            ActionOption("open", value_impacts={"strategic_direction": 0.2}),
        )
        reply_a = WorldAction(
            PoliticalAction("organize", {"immediate": {"x": 1}, "medium": {}, "long": {}}),
            ActionOption(
                "organize",
                value_impacts={"organization_success": 0.7},
                instrumental_impacts={"capacity": 0.7},
            ),
        )
        reply_b = WorldAction(
            PoliticalAction("attack", {"immediate": {"x": -1}, "medium": {}, "long": {}}),
            ActionOption(
                "attack",
                value_impacts={"organization_success": -0.5},
                institutional_deviation=0.8,
                instrumental_impacts={"capacity": -0.4},
            ),
        )
        result = LayeredSimulationOrchestrator(
            state,
            {
                "start": SimulationNodeV3("start", "Merz", (opening,)),
                "reply": SimulationNodeV3("reply", "Frei", (reply_a, reply_b)),
            },
            FreeAgentDecisionEngine.from_json(CARDS),
            InformationFilter({"Merz": {"x": AccessRule(0.9)}, "Frei": {"x": AccessRule(0.9)}}),
            {},
            config,
            reporting_policy=ScenarioReportingPolicy.diagnostics_only(),
        ).run("start", max_steps=1)
        forecast = result["trace"][0]["forecast_responses"]["open"]
        self.assertEqual(forecast[0]["owner"], "Frei")
        self.assertIn("attack", forecast[0]["perceived_action_menu"])
        self.assertEqual(result["trace"][0]["decision_source"], "persona_v2_compatibility")

    def test_world_action_can_update_multiple_actor_pss_states(self):
        state = PoliticalState({"x": StateVariable("x", 50)}, {}, {})
        action = WorldAction(
            PoliticalAction("shock", {"immediate": {"x": -1}, "medium": {}, "long": {}}),
            ActionOption("shock", value_impacts={"strategic_direction": 0.1}),
            actor_events={
                "Merz": (WorldEvent("challenge", "authority_challenge", 0.6, ("authority_challenge",)),),
                "Soeder": (WorldEvent("exposure", "public_signal", 0.3, ("public_signal",)),),
            },
        )
        config = LayeredConfiguration.from_environment_json(ENV, RATIONALITY)
        result = LayeredSimulationOrchestrator(
            state,
            {"n": SimulationNodeV3("n", "Merz", (action,))},
            FreeAgentDecisionEngine.from_json(CARDS),
            InformationFilter({"Merz": {"x": AccessRule(0.9)}}),
            {},
            config,
            reporting_policy=ScenarioReportingPolicy.diagnostics_only(),
        ).run("n")
        updates = result["trace"][0]["operational_feedback"]["pss_updates"]
        self.assertEqual({row["actor"] for row in updates}, {"Merz", "Soeder"})

    def test_objective_precheck_occurs_after_choice_and_blocks_world_mutation(self):
        state = PoliticalState({"x": StateVariable("x", 50)}, {}, {})
        action = WorldAction(
            PoliticalAction("dismiss", {"immediate": {"x": 25}, "medium": {}, "long": {}}),
            ActionOption("dismiss", value_impacts={"political_authority": 0.9}),
            intent=Intent("i1", "Soeder", "dismiss_chancellor", "Merz"),
        )
        config = LayeredConfiguration.from_environment_json(ENV, RATIONALITY)
        result = LayeredSimulationOrchestrator(
            state,
            {"n": SimulationNodeV3("n", "Soeder", (action,))},
            FreeAgentDecisionEngine.from_json(CARDS),
            InformationFilter({"Soeder": {"x": AccessRule(0.9)}}),
            {},
            config,
            reporting_policy=ScenarioReportingPolicy.diagnostics_only(),
            objective_check_engine=build_gg_check_engine(),
            check_context_provider=lambda _: CheckContext(
                now_hours=100,
                bundestag=BundestagState(630),
                actor_roles={"Soeder": frozenset({"land_government"})},
                office_holders={"federal_chancellor": "Merz"},
            ),
        ).run("n")
        turn = result["trace"][0]
        self.assertEqual(turn["institutional_resolution"]["resolution"], "blocked")
        self.assertEqual(result["world_state"]["variables"]["x"]["value"], 50)


if __name__ == "__main__":
    unittest.main()

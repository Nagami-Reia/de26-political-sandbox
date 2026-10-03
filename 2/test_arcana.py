import unittest
import copy
import json
from pathlib import Path

from kfrage_model.arcana import ArcanaConfig, ArcanaService
from kfrage_model.arcana.engine.models import Draw, Orientation
from kfrage_model.arcana.engine.resolver import HistoricalResolver
from kfrage_model.arcana.engine.spread import PetitEtteillaDeck
from kfrage_model.arcana.hakoniwa import ArcanaDecisionAdapter
from kfrage_model.arcana.reporting import ArcanaVisualReportRenderer
from kfrage_model.arcana.report_trace import ArcanaReportTraceCompiler
from kfrage_model.experiments.arcana_mini_test_01 import (
    run as run_mini_test_01,
    visual_audits,
    visual_preview_audits,
)
from kfrage_model.persona_v2 import ActionOption, FreeAgentDecisionEngine


ROOT = Path(__file__).parent
CARDS = ROOT / "personality_cards_2026" / "cards_pss.json"


class ArcanaTests(unittest.TestCase):
    def test_synthetic_mini_lab_covers_confirm_indeterminate_and_near_tie_change(self):
        result = run_mini_test_01(10)
        self.assertTrue(result["success_criteria"]["all_three_behaviors_observed"])
        self.assertTrue(result["success_criteria"]["c_never_selected"])
        self.assertEqual(
            result["scan"]["selected_action_counts"]["C_ESCALATE"],
            0,
        )

    def test_arcana_visual_report_uses_compact_trace_and_lazy_detail(self):
        result = run_mini_test_01(10)
        compact = ArcanaReportTraceCompiler().compile(visual_audits(result))
        document = ArcanaVisualReportRenderer().render_document(compact, title="Mini Test")
        self.assertIn("Chronicle", document)
        self.assertIn("Nodes", document)
        self.assertIn("A_CONTAIN", document)
        self.assertIn("B_CONCEDE", document)
        self.assertIn("is-reversed", document)
        self.assertIn("historical meaning", document)
        self.assertIn('"identity_status":"UNASSIGNED"', document)
        self.assertNotIn("AdviceType.", document)
        self.assertIn('id="arcana-detail-host"', document)
        # Full cards are constructed by JavaScript only after a node is opened.
        self.assertNotIn('<button type="button" class="arc-playing-card"', document)
        self.assertIn("host.replaceChildren(detail)", document)
        self.assertIn("host.replaceChildren()", document)

        clash_document = ArcanaVisualReportRenderer().render_document(
            visual_preview_audits(result), title="Clash Test"
        )
        self.assertIn("ADVISORY COLLISION", clash_document)
        self.assertIn("Merz", clash_document)
        self.assertIn("Soeder", clash_document)

    def test_report_trace_deduplicates_history_and_stores_pss_as_deltas(self):
        result = run_mini_test_01(10)
        compact = ArcanaReportTraceCompiler().compile(visual_audits(result))
        self.assertEqual(compact["schema_version"], "arcana-report-trace-1.0")
        self.assertFalse(compact["render_contract"]["llm_required"])
        self.assertEqual(compact["render_contract"]["detail_mount_policy"], "AT_MOST_ONE")
        self.assertIn("snapshot", compact["nodes"][0]["pss"]["M"])
        self.assertIn("delta", compact["nodes"][1]["pss"]["M"])
        self.assertNotIn("base_meanings", json.dumps(compact))
        for node in compact["nodes"]:
            for reference in node["reading"]["rules"]:
                self.assertIn(reference["id"], compact["dictionary"]["rules"])
            for code in node["reading"]["cards"]:
                self.assertIn(code[-1], ("U", "R"))
                self.assertIn(code[:-1], compact["dictionary"]["cards"])

    def test_500_node_report_keeps_initial_dom_to_collapsed_summaries(self):
        seed_audits = visual_audits(run_mini_test_01(10))
        audits = []
        for index in range(500):
            row = copy.deepcopy(seed_audits[index % len(seed_audits)])
            row["node"] = f"scale_node_{index:03d}"
            audits.append(row)
        compact = ArcanaReportTraceCompiler().compile(audits)
        fragment = ArcanaVisualReportRenderer().render_fragment(compact)
        self.assertEqual(len(compact["nodes"]), 500)
        self.assertEqual(fragment.count('class="arc-node-summary"'), 500)
        self.assertNotIn('<button type="button" class="arc-playing-card"', fragment)
        self.assertLess(
            len(json.dumps(compact, ensure_ascii=False)),
            len(json.dumps(audits, ensure_ascii=False, default=str)),
        )

    def test_deck_is_32_piquet_cards_plus_carte_blanche(self):
        deck = PetitEtteillaDeck()
        self.assertEqual(len(deck.definitions), 33)
        self.assertIn("CB", deck.definitions)
        self.assertEqual(deck.definitions["CB"].etteilla_number, 1)
        self.assertEqual(deck.definitions["7C"].etteilla_number, 30)

    def test_coup_de_douze_is_seeded_distinct_and_12_plus_2(self):
        deck = PetitEtteillaDeck()
        first = deck.coup_de_douze(12345)
        second = deck.coup_de_douze(12345)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 14)
        self.assertEqual(len({draw.card_id for draw in first}), 14)
        self.assertEqual([draw.role for draw in first[-2:]], ["TURN_CARD", "BOTTOM_CARD"])

    def test_verified_meeting_12_plus_19_resolves_politics(self):
        deck = PetitEtteillaDeck()
        resolver = HistoricalResolver()
        draws = (
            Draw("JH", Orientation.UPRIGHT, 1),
            Draw("JS", Orientation.REVERSED, 2),
        )
        rows = resolver.resolve_meetings(draws, deck.definitions)
        self.assertEqual(rows[0].meaning, "politics")

    def test_verified_three_upright_kings_resolve_consultation(self):
        deck = PetitEtteillaDeck()
        resolver = HistoricalResolver()
        draws = tuple(Draw(card, Orientation.UPRIGHT, i + 1)
                      for i, card in enumerate(("KD", "KH", "KS")))
        rows = resolver.resolve_multiples(draws, deck.definitions)
        self.assertEqual(rows[0].meaning, "consultation")

    def test_run_replays_exactly(self):
        service = ArcanaService(ArcanaConfig(enabled=True, master_seed=77))
        run = service.run_reading("node-x", "Merz")
        self.assertEqual(run.payload(), service.replay(run.run_id).payload())

    def test_arcana_cannot_overturn_a_large_rational_gap(self):
        personas = FreeAgentDecisionEngine.from_json(CARDS)
        service = ArcanaService(ArcanaConfig(enabled=True, master_seed=9))
        run = service.run_reading("node-y", "Merz")
        actions = (
            ActionOption("dominant", upside=0.800, downside=0.100, uncertainty=0.100),
            ActionOption("gamble", upside=1.000, downside=0.800, uncertainty=0.800, irreversibility=0.800),
        )
        chosen, trace = ArcanaDecisionAdapter().adapt(
            "dominant", {"dominant": 0.900, "gamble": 0.300}, actions, run.advice,
            personas.cards["Merz"], personas.runtime["Merz"], 1.000,
        )
        self.assertEqual(chosen, "dominant")
        self.assertNotEqual(trace["adoption_status"], "ACCEPT_ADVICE")

    def test_conflict_runs_independent_readings_and_pss_mediation(self):
        personas = FreeAgentDecisionEngine.from_json(CARDS)
        service = ArcanaService(ArcanaConfig(enabled=True, master_seed=11))
        result = service.run_conflict(
            "conflict-node", "Merz", "Soeder",
            personas.cards["Merz"], personas.runtime["Merz"],
            personas.cards["Soeder"], personas.runtime["Soeder"],
        )
        self.assertNotEqual(
            result["primary_reading"]["seed"],
            result["counterparty_reading"]["seed"],
        )
        self.assertIn("primary_pss_mediation", result["interaction"])
        self.assertIn("counterparty_pss_mediation", result["interaction"])
        self.assertIn("causal_boundary", result["interaction"])


if __name__ == "__main__":
    unittest.main()

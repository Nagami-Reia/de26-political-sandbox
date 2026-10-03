import unittest

from kfrage_model.checks.base import CheckStatus, Resolution
from kfrage_model.checks.constitutional import build_gg_check_engine
from kfrage_model.checks.context import BundestagState, CheckContext, FederalLawExecution
from kfrage_model.checks.engine import InstitutionalResolver
from kfrage_model.interaction.intents import IntentCompiler
from kfrage_model.procedures.state import ProcedureBook, ProcedureState


def context(*, now=100, procedures=(), laws=None, facts=None):
    roles = {
        "Merz": frozenset({"federal_chancellor"}),
        "Steinmeier": frozenset({"federal_president"}),
        "Frei": frozenset({"bundestag_member"}),
        "Bundestag": frozenset({"bundestag"}),
        "Bundesregierung": frozenset({"federal_government"}),
        "Wadephul": frozenset({"federal_minister", "federal_minister:foreign"}),
        "Pistorius": frozenset({"federal_minister", "federal_minister:defence"}),
        "FederalOffice": frozenset({"federal_authority", "highest_federal_authority"}),
        "NRW": frozenset({"land_authority", "land_government", "highest_land_authority"}),
        "Soeder": frozenset({"land_government"}),
    }
    return CheckContext(
        now_hours=now,
        bundestag=BundestagState(630),
        actor_roles=roles,
        office_holders={
            "federal_chancellor": "Merz",
            "federal_president": "Steinmeier",
        },
        procedures=ProcedureBook({item.procedure_id: item for item in procedures}),
        federal_laws=laws or {},
        facts=facts or {},
    )


def intent(actor, verb, *, target=None, payload=None, key="i"):
    return IntentCompiler().compile(
        intent_id=key, actor=actor, verb=verb, target=target, payload=payload,
    )


def constitutional_result(bundle):
    return bundle.layers[0].results[0]


class ConstitutionalCheckTests(unittest.TestCase):
    def setUp(self):
        self.engine = build_gg_check_engine()

    def test_actor_may_generate_direct_chancellor_dismissal_but_checker_blocks_it(self):
        bundle = self.engine.check(context(), intent("Soeder", "dismiss_bundeskanzler", target="Merz"))
        result = constitutional_result(bundle)
        self.assertEqual(bundle.resolution, Resolution.BLOCKED)
        self.assertEqual(result.reason, "NO_DIRECT_DISMISSAL_AUTHORITY")
        self.assertIn("replace_chancellor", result.alternatives)

    def test_art67_routes_then_waits_then_passes_constructive_vote(self):
        routed = self.engine.check(context(), intent("Frei", "replace_chancellor", target="Merz"))
        self.assertEqual(routed.resolution, Resolution.REQUIRES_PROCEDURE)

        procedure = ProcedureState(
            "p67", "GG67_CONSTRUCTIVE_NO_CONFIDENCE", "MOTION_FILED", 90,
            candidate="Wuest", votes_yes=316, metadata={"vote_completed": True},
        )
        waiting = self.engine.check(
            context(now=120, procedures=(procedure,)),
            intent("Frei", "replace_chancellor", payload={"procedure_id": "p67"}),
        )
        self.assertEqual(waiting.resolution, Resolution.PENDING)
        passed = self.engine.check(
            context(now=140, procedures=(procedure,)),
            intent("Frei", "replace_chancellor", payload={"procedure_id": "p67"}),
        )
        result = constitutional_result(passed)
        self.assertEqual(passed.resolution, Resolution.EXECUTABLE)
        self.assertIn("PRESIDENT_MUST_DISMISS_AND_APPOINT", result.effects)

    def test_art64_separates_chancellor_proposal_from_presidential_act(self):
        proposal = self.engine.check(
            context(), intent("Merz", "propose_appoint_minister", target="Wadephul")
        )
        self.assertEqual(proposal.resolution, Resolution.REQUIRES_PROCEDURE)
        procedure = ProcedureState(
            "p64", "GG64_MINISTER_APPOINTMENT", "PROPOSED", 100,
            target="Wadephul", metadata={"chancellor_proposal": True},
        )
        appointment = self.engine.check(
            context(procedures=(procedure,)),
            intent("Steinmeier", "appoint_minister", target="Wadephul", payload={"procedure_id": "p64"}),
        )
        self.assertEqual(appointment.resolution, Resolution.EXECUTABLE)
        self.assertIn("APPOINT_FEDERAL_MINISTER", constitutional_result(appointment).effects)

    def test_art65_preserves_ministerial_portfolio_autonomy_within_guidelines(self):
        valid = self.engine.check(
            context(),
            intent("Wadephul", "manage_ministry_portfolio", payload={
                "portfolio": "foreign", "within_policy_guidelines": True,
            }),
        )
        self.assertEqual(valid.resolution, Resolution.EXECUTABLE)
        invalid = self.engine.check(
            context(),
            intent("Merz", "manage_ministry_portfolio", payload={
                "portfolio": "foreign", "within_policy_guidelines": True,
            }),
        )
        self.assertEqual(invalid.resolution, Resolution.BLOCKED)

    def test_art68_requires_chancellor_motion_and_48_hours(self):
        procedure = ProcedureState(
            "p68", "GG68_CONFIDENCE_MOTION", "MOTION_FILED", 90,
            votes_yes=300, metadata={"vote_completed": True},
        )
        waiting = self.engine.check(
            context(now=120, procedures=(procedure,)),
            intent("Merz", "request_confidence", payload={"procedure_id": "p68"}),
        )
        self.assertEqual(waiting.resolution, Resolution.PENDING)
        failed = self.engine.check(
            context(now=140, procedures=(procedure,)),
            intent("Merz", "request_confidence", payload={"procedure_id": "p68"}),
        )
        self.assertIn("OPEN_DISSOLUTION_WINDOW_21_DAYS", constitutional_result(failed).effects)

    def test_art83_default_land_execution_and_special_federal_direct_domain(self):
        laws = {
            "ordinary": FederalLawExecution("ordinary"),
            "air": FederalLawExecution("air", domain="AIR_TRANSPORT_ADMINISTRATION"),
        }
        federal_attempt = self.engine.check(
            context(laws=laws),
            intent("FederalOffice", "execute_federal_law", payload={"law_id": "ordinary"}),
        )
        self.assertEqual(federal_attempt.resolution, Resolution.BLOCKED)
        land_execution = self.engine.check(
            context(laws=laws),
            intent("NRW", "execute_federal_law", payload={"law_id": "ordinary"}),
        )
        self.assertEqual(land_execution.resolution, Resolution.EXECUTABLE)
        air_execution = self.engine.check(
            context(laws=laws),
            intent("FederalOffice", "execute_federal_law", payload={"law_id": "air"}),
        )
        self.assertEqual(air_execution.resolution, Resolution.EXECUTABLE)

    def test_art84_and_85_do_not_treat_instruction_powers_as_identical(self):
        laws = {
            "own": FederalLawExecution("own", bundesrat_consent=False),
            "commission": FederalLawExecution("commission", administration_mode="FEDERAL_COMMISSION"),
        }
        own = self.engine.check(
            context(laws=laws),
            intent("Bundesregierung", "issue_individual_instruction", payload={"law_id": "own"}),
        )
        self.assertEqual(own.resolution, Resolution.BLOCKED)
        commissioned = self.engine.check(
            context(laws=laws),
            intent("FederalOffice", "issue_individual_instruction", payload={
                "law_id": "commission", "target_level": "highest_land_authority",
            }),
        )
        self.assertEqual(commissioned.resolution, Resolution.EXECUTABLE)

    def test_art87_middle_authority_requires_all_four_conditions(self):
        blocked_bundle = self.engine.check(
            context(),
            intent("Bundesregierung", "create_federal_authority", payload={
                "authority_level": "middle_authority",
                "federal_law_enacted": True,
                "federal_legislative_competence": True,
                "new_federal_task": True,
                "urgent_need": True,
                "bundesrat_consent": False,
                "bundestag_yes_votes": 316,
            }),
        )
        self.assertEqual(blocked_bundle.resolution, Resolution.BLOCKED)
        self.assertIn("bundesrat_consent", constitutional_result(blocked_bundle).missing_conditions)

    def test_same_truth_and_intent_are_deterministic(self):
        ctx = context()
        item = intent("Soeder", "dismiss_chancellor", target="Merz")
        first = self.engine.check(ctx, item).payload()
        second = self.engine.check(ctx, item).payload()
        self.assertEqual(first, second)
        self.assertEqual(
            InstitutionalResolver().resolve(self.engine.check(ctx, item)).resolution,
            Resolution.BLOCKED,
        )

    def test_chancellor_command_requires_promulgated_defence_case(self):
        before = self.engine.check(context(), intent("Merz", "assume_defence_command"))
        self.assertEqual(before.resolution, Resolution.BLOCKED)
        after = self.engine.check(
            context(facts={"defence_case_promulgated": True}),
            intent("Merz", "assume_defence_command"),
        )
        self.assertEqual(after.resolution, Resolution.EXECUTABLE)
        self.assertIn("COMMAND_AUTHORITY_TRANSFERS_TO_CHANCELLOR",
                      constitutional_result(after).effects)

    def test_art115a_requires_attack_threshold_vote_bundesrat_and_promulgation(self):
        no_threshold = self.engine.check(
            context(), intent("Bundestag", "determine_state_of_defence"))
        self.assertEqual(no_threshold.resolution, Resolution.BLOCKED)
        procedure = ProcedureState(
            "p115", "GG115A_DEFENCE_CASE", "VOTE_COMPLETED", 100,
            votes_yes=420, votes_no=180,
            metadata={"vote_completed": True, "federal_government_application": True,
                      "bundesrat_consent": True},
        )
        determined = self.engine.check(
            context(procedures=(procedure,), facts={
                "federal_territory_attacked_by_armed_force": True,
            }),
            intent("Bundestag", "determine_state_of_defence",
                   payload={"procedure_id": "p115"}),
        )
        self.assertEqual(determined.resolution, Resolution.EXECUTABLE)
        self.assertIn("DEFENCE_CASE_DETERMINED", constitutional_result(determined).effects)
        not_yet = self.engine.check(context(), intent("Merz", "assume_defence_command"))
        self.assertEqual(not_yet.resolution, Resolution.BLOCKED)

    def test_state_of_tension_and_civilian_object_protection_are_separate_steps(self):
        procedure = ProcedureState(
            "p80", "GG80A_STATE_OF_TENSION", "VOTE_COMPLETED", 100,
            votes_yes=410, votes_no=190, metadata={"vote_completed": True},
        )
        tension = self.engine.check(
            context(procedures=(procedure,)),
            intent("Bundestag", "determine_state_of_tension", payload={"procedure_id": "p80"}),
        )
        self.assertEqual(tension.resolution, Resolution.EXECUTABLE)
        blocked_protection = self.engine.check(
            context(), intent("Bundesregierung", "deploy_armed_forces_to_protect_civilian_objects"))
        self.assertEqual(blocked_protection.resolution, Resolution.BLOCKED)
        allowed_protection = self.engine.check(
            context(facts={"state_of_tension_determined": True}),
            intent("Bundesregierung", "deploy_armed_forces_to_protect_civilian_objects"),
        )
        self.assertEqual(allowed_protection.resolution, Resolution.EXECUTABLE)


if __name__ == "__main__":
    unittest.main()

import unittest

from kfrage_model.parliamentary_vote import (
    BlocVotePrior, ParliamentaryVoteModel, VoteFeedback, VoteRule,
)
from kfrage_model.political_activity import (
    ActivityContext, ActivityTemplate, PoliticalActivity,
    PoliticalActivityModel, RoutineActivityProgram,
)
from kfrage_model.political_state import PoliticalState, StateVariable
from kfrage_model.realtime_polling import PollSeriesSpec, RealtimePollingTracker


class ParliamentaryVoteTests(unittest.TestCase):
    def setUp(self):
        self.model = ParliamentaryVoteModel()
        self.rule = VoteRule("simple_cast", 100)
        self.blocs = (
            BlocVotePrior("government", 55, .98, .95, .04, .01, hidden_defection_sigma=.02),
            BlocVotePrior("opposition", 45, .95, .05, .93, .02, hidden_defection_sigma=.01),
        )

    def test_forecast_has_explicit_conclusion_and_margin(self):
        forecast = self.model.forecast("bill", "third_reading", self.rule, self.blocs)
        self.assertIn(forecast.conclusion, {"clear_pass", "lean_pass", "knife_edge_pass", "knife_edge_fail", "lean_fail", "clear_fail"})
        self.assertGreater(forecast.expected_margin, 0)

    def test_seeded_vote_simulation_is_reproducible(self):
        first = self.model.simulate(self.rule, self.blocs, 300, 42)
        second = self.model.simulate(self.rule, self.blocs, 300, 42)
        self.assertEqual(first, second)

    def test_vote_feedback_updates_people_and_environment(self):
        state = PoliticalState(
            {"leader_support": StateVariable("leader_support", 40), "coalition_trust": StateVariable("coalition_trust", 50)},
            {"Leader:government": 50}, {"faction_rebellion": 20},
        )
        result = self.model.settle("bill", "third", self.rule, 52, 45, 2, 1)
        feedback = {"narrow_pass": VoteFeedback("narrow_pass", {"leader_support": 1, "coalition_trust": 2}, {"Leader:government": 3}, {"faction_rebellion": -2})}
        self.model.apply_feedback(state, result, feedback)
        self.assertEqual(state.variables["leader_support"].value, 41)
        self.assertEqual(state.capital["Leader:government"], 53)


class PoliticalActivityTests(unittest.TestCase):
    def setUp(self):
        self.model = PoliticalActivityModel({
            "speech": ActivityTemplate("speech", {"party_poll": 1.0, "visibility": 2.0}, base_reach=.4, base_credibility=.6),
        })

    def test_low_attention_activity_can_have_zero_detectable_poll_effect(self):
        activity = PoliticalActivity("A1", 1, "Leader", "speech", "economy")
        context = ActivityContext(.2, .4, .9, .8, detection_floor=.1)
        outcome = self.model.resolve(activity, context, "Leader:capital")
        self.assertEqual(outcome.effects["party_poll"], 0)
        self.assertEqual(outcome.impact_class, "no_detectable_poll_effect")

    def test_seeded_activity_generation_is_reproducible(self):
        program = RoutineActivityProgram("Leader", .7, {"speech": 1}, {"economy": 1}, "Leader:capital")
        self.assertEqual(self.model.generate((program,), 10, 9, True), self.model.generate((program,), 10, 9, True))


class RealtimePollingTests(unittest.TestCase):
    def test_tracker_records_baseline_and_every_event_even_when_rounded_value_is_flat(self):
        state = PoliticalState({"party_poll": StateVariable("party_poll", 20.0)}, {}, {})
        tracker = RealtimePollingTracker("run", "env", (
            PollSeriesSpec("party_poll", "Party", "electorate", "vote_intention", "DE", retention=.7, publication_grid=.5),
        ), "2026-09-18T12:00:00+02:00")
        tracker.record_baseline(state)
        state.variables["party_poll"] = StateVariable("party_poll", 20.1)
        tracker.record(state, event_id="E1", actor="Leader", action="speech", event_kind="activity")
        payload = tracker.to_dict()
        nowcasts = [p for p in payload["support_points"] if p["measure"].endswith("nowcast")]
        self.assertEqual([p["step"] for p in nowcasts], [0, 1])
        self.assertEqual([p["value"] for p in nowcasts], [20.0, 20.0])

    def test_tracker_accumulates_sub_grid_changes_before_publication_rounding(self):
        state = PoliticalState({"party_poll": StateVariable("party_poll", 20.0)}, {}, {})
        tracker = RealtimePollingTracker("run", "env", (
            PollSeriesSpec("party_poll", "Party", "electorate", "vote_intention", "DE",
                           retention=1.0, publication_grid=.5),
        ), "2026-09-18T12:00:00+02:00")
        tracker.record_baseline(state)
        for index in range(3):
            state.variables["party_poll"] = StateVariable("party_poll", 20.1 + index * .1)
            tracker.record(state, event_id=f"E{index}", actor="Leader", action="speech",
                           event_kind="activity")
        nowcasts = [p for p in tracker.to_dict()["support_points"]
                    if p["measure"].endswith("nowcast")]
        self.assertEqual([p["value"] for p in nowcasts], [20.0, 20.0, 20.0, 20.5])


if __name__ == "__main__":
    unittest.main()

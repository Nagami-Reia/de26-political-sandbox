import unittest
from kfrage_model.information_filter import AccessRule,InformationFilter
from kfrage_model.political_state import PoliticalAction,PoliticalState,PressureRule,StateVariable
from kfrage_model.strategic_game import ActorDecisionModel,DecisionNode,StrategicGame

def action(key,delta,**kw): return PoliticalAction(key,{"immediate":{"x":delta},"medium":{},"long":{}},**kw)

class POMDGTests(unittest.TestCase):
    def test_fog_of_war_produces_different_beliefs_without_changing_truth(self):
        s=PoliticalState({"x":StateVariable("x",50,10,.1)},{},{})
        f=InformationFilter({"A":{"x":AccessRule(.9,5,source="staff")},"B":{"x":AccessRule(.4,-4,source="media")}})
        self.assertEqual(f.observe("A",s).beliefs["x"].estimate,55)
        self.assertEqual(f.observe("B",s).beliefs["x"].estimate,46)
        self.assertEqual(s.variables["x"].value,50)

    def test_counterfactual_observation_does_not_pollute_persistent_belief(self):
        s=PoliticalState({"x":StateVariable("x",50)},{},{})
        f=InformationFilter({"A":{"x":AccessRule(.8)}})
        f.observe("A",s,commit=True)
        hypothetical=s.clone(); hypothetical.variables["x"]=StateVariable("x",90)
        f.observe("A",hypothetical,commit=False)
        self.assertEqual(f.states["A"].beliefs["x"].estimate,50)

    def test_pressure_threshold_creates_lock(self):
        s=PoliticalState({"x":StateVariable("x",50)},{},{"conflict":65})
        a=PoliticalAction("raise",{"immediate":{},"medium":{},"long":{}},pressure_delta={"conflict":5})
        s.apply(a,(PressureRule("conflict",70,"crisis",{},("crisis_mode",)),))
        self.assertIn("crisis_mode",s.locks)

    def test_hard_threshold_rejects_attractive_but_infeasible_action(self):
        s=PoliticalState({"x":StateVariable("x",2,1)},{},{})
        info=InformationFilter({"A":{"x":AccessRule(.99)}})
        model=ActorDecisionModel("A",{"immediate":{"x":1},"medium":{},"long":{}},hard_minimums={"x":0},planning_depth=0)
        node=DecisionNode("n","A",(action("bad",-5,feasibility=.9),action("safe",0,feasibility=.9)),("A",))
        out=StrategicGame(s,{"n":node},{"A":model},info).run("n")
        self.assertEqual(out["trace"][0]["chosen_action"],"safe")

if __name__=="__main__": unittest.main()

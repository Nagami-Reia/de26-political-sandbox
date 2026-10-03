"""Legacy v1 node-by-node political decision engine.

The environment supplies state variables and action consequences.  Each actor
scores every changed variable through a replaceable personality profile; only the
node owner chooses.  Scores are comparison indices, never measurements.

New scenarios should use ``simulation_orchestrator.py``.  This module remains a
compatibility adapter for historical baselines and sensitivity archives.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Mapping

def clamp(x, lo=0.0, hi=100.0): return max(lo, min(hi, x))

@dataclass(frozen=True)
class Variable:
    key: str
    value: float
    scale: float = 10.0
    uncertainty: float = 0.0
    evidence: str = "MODEL_STATE"

@dataclass(frozen=True)
class Action:
    key: str
    deltas: Mapping[str, float]
    downside: Mapping[str, float] = field(default_factory=dict)
    upside: Mapping[str, float] = field(default_factory=dict)
    feasibility: float = 1.0
    tags: tuple[str, ...] = ()

@dataclass(frozen=True)
class ActorProfile:
    actor: str
    weights: Mapping[str, float]
    targets: Mapping[str, float] = field(default_factory=dict)
    loss_aversion: float = 1.0
    upside_appetite: float = 0.0
    feasibility_weight: float = 1.0
    decision_rule: str = "weighted expected utility"

@dataclass(frozen=True)
class Node:
    key: str
    decision_maker: str
    actions: tuple[Action, ...]
    visible_to: tuple[str, ...]

class RoguelikeEngine:
    def __init__(self, variables: Mapping[str, Variable], profiles: Mapping[str, ActorProfile]):
        self.variables=dict(variables); self.profiles=dict(profiles); self.trace=[]

    def evaluate(self, actor: str, action: Action):
        p=self.profiles[actor]; rows=[]; total=0.0
        for key,delta in action.deltas.items():
            v=self.variables[key]; weight=float(p.weights.get(key,0.0)); normalized=delta/max(v.scale,1e-9)
            direct=weight*normalized
            target=p.targets.get(key); expectation=0.0 if target is None else -abs((v.value+delta)-target)/max(v.scale,1e-9)*abs(weight)*.20
            loss=p.loss_aversion*abs(weight*min(0,action.downside.get(key,0.0)/max(v.scale,1e-9)))
            upside=p.upside_appetite*abs(weight*max(0,action.upside.get(key,0.0)/max(v.scale,1e-9)))
            contribution=direct+expectation-loss+upside
            total+=contribution
            rows.append({"variable":key,"before":v.value,"delta":delta,"after":v.value+delta,"weight":weight,
                         "direct":round(direct,4),"expectation_fit":round(expectation,4),"downside_penalty":round(loss,4),
                         "upside_option":round(upside,4),"contribution":round(contribution,4)})
        feasibility_term=p.feasibility_weight*(action.feasibility-.5)
        total+=feasibility_term
        return {"actor":actor,"action":action.key,"variable_evaluations":rows,
                "feasibility":action.feasibility,"feasibility_term":round(feasibility_term,4),"total":round(total,4),
                "decision_rule":p.decision_rule}

    def play(self,node:Node):
        matrix={actor:{a.key:self.evaluate(actor,a) for a in node.actions} for actor in node.visible_to}
        owner=matrix[node.decision_maker]
        chosen=max(node.actions,key=lambda a:(owner[a.key]["total"],a.key))
        before={k:v.value for k,v in self.variables.items()}
        for key,delta in chosen.deltas.items():
            v=self.variables[key]; self.variables[key]=Variable(key,clamp(v.value+delta),v.scale,v.uncertainty,v.evidence)
        event={"node":node.key,"decision_maker":node.decision_maker,"chosen_action":chosen.key,
               "all_actor_action_evaluations":matrix,"state_before":before,
               "state_after":{k:v.value for k,v in self.variables.items()}}
        self.trace.append(event); return event

    def payload(self):
        return {"schema_version":"roguelike-1.0","variables":{k:asdict(v) for k,v in self.variables.items()},"trace":self.trace,
                "warning":"Scores compare actions inside this model; they are not observed quantities or real-world probabilities."}

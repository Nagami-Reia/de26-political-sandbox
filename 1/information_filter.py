"""Fog-of-war: transform one reality into actor-specific belief states."""
from __future__ import annotations
import random
from copy import deepcopy
from dataclasses import dataclass,field,asdict
from typing import Mapping
from .political_state import PoliticalState

@dataclass(frozen=True)
class AccessRule:
    access: float
    bias: float=0.0
    noise: float=0.0
    source: str="public"

@dataclass
class Belief:
    estimate: float
    confidence: float
    source: str
    last_truth: float|None=None

@dataclass
class BeliefState:
    actor: str
    beliefs: dict[str,Belief]=field(default_factory=dict)
    source_trust: dict[str,float]=field(default_factory=dict)

class InformationFilter:
    def __init__(self,rules:Mapping[str,Mapping[str,AccessRule]],seed:int=0,stochastic:bool=False):
        self.rules={a:dict(v) for a,v in rules.items()}; self.rng=random.Random(seed); self.stochastic=stochastic
        self.states={a:BeliefState(a) for a in rules}

    def observe(self,actor:str,state:PoliticalState,commit:bool=False):
        # Counterfactual branches must never leak back into an actor's real beliefs.
        bs=self.states[actor] if commit else deepcopy(self.states[actor]); rules=self.rules.get(actor,{})
        for key,var in state.variables.items():
            r=rules.get(key,AccessRule(.35,0,var.uncertainty,"public")); trust=bs.source_trust.get(r.source,.75)
            noise=self.rng.gauss(0,r.noise) if self.stochastic else 0.0
            estimate=max(0,min(100,var.value+r.bias+noise))
            confidence=max(.05,min(.99,r.access*trust*(1-var.uncertainty)))
            prior=bs.beliefs.get(key)
            if prior:
                alpha=confidence/(confidence+prior.confidence)
                estimate=alpha*estimate+(1-alpha)*prior.estimate
                confidence=max(prior.confidence*.85,confidence)
            bs.beliefs[key]=Belief(round(estimate,4),round(confidence,4),r.source,var.value)
        return bs

    def reveal(self,actor:str,key:str,truth:float):
        bs=self.states[actor]; b=bs.beliefs.get(key)
        if not b:return
        error=abs(b.estimate-truth); old=bs.source_trust.get(b.source,.75)
        bs.source_trust[b.source]=max(.1,min(.99,.8*old+.2*max(0,1-error/20)))

    @staticmethod
    def payload(bs:BeliefState): return {"actor":bs.actor,"beliefs":{k:asdict(v) for k,v in bs.beliefs.items()},"source_trust":bs.source_trust}

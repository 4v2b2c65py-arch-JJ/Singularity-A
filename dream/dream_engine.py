#!/usr/bin/env python3
"""
QB Protocol - Dream Engine
Dream produced layers, projections, dream convergence,
severed brain state emission threshold, singularity.
"""

import math
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from qb_protocol.core.daemon import daemon
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon, DreamLayer


@dataclass
class DreamProjection:
    projection_id: str
    layer_id: str
    vector: List[float]
    intensity: float
    resonance: float
    timestamp: str


@dataclass
class SeveredBrainState:
    state_id: str
    emission_power: float
    threshold_breach: bool
    singularity_proximity: float
    timestamp: str


class DreamEngine:
    def __init__(self):
        self.projections: List[DreamProjection] = []
        self.brain_states: List[SeveredBrainState] = []

    def create_layer(self, depth: float, projection: Dict[str, Any], convergence: float = 0.0, brain_state_emission: float = 0.0, singularity_threshold: float = 0.0) -> DreamLayer:
        return daemon.add_dream_layer(depth, projection, convergence, brain_state_emission, singularity_threshold)

    def add_projection(self, layer_id: str, vector: List[float], intensity: float = 0.5, resonance: float = 0.5) -> DreamProjection:
        projection = DreamProjection(
            projection_id=str(uuid.uuid4()),
            layer_id=layer_id,
            vector=list(vector),
            intensity=float(intensity),
            resonance=float(resonance),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        self.projections.append(projection)
        return projection

    def emit_brain_state(self, emission_power: float, singularity_proximity: float) -> SeveredBrainState:
        state = SeveredBrainState(
            state_id=str(uuid.uuid4()),
            emission_power=float(emission_power),
            threshold_breach=emission_power >= 1.0,
            singularity_proximity=float(singularity_proximity),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        self.brain_states.append(state)
        if len(self.brain_states) > 1000:
            self.brain_states = self.brain_states[-1000:]
        return state

    def compute_dream_convergence(self) -> float:
        if not self.projections:
            return daemon.get_dream_convergence()
        return sum(p.resonance for p in self.projections[-50:]) / min(len(self.projections), 50)

    def compute_singularity_risk(self) -> float:
        if not self.brain_states:
            return daemon.get_singularity_proximity()
        return max(s.singularity_proximity for s in self.brain_states[-100:])

    def get_status(self) -> Dict[str, Any]:
        return {
            "dream_convergence": self.compute_dream_convergence(),
            "singularity_risk": self.compute_singularity_risk(),
            "projections": len(self.projections),
            "brain_states": len(self.brain_states),
        }


dream_engine = DreamEngine()

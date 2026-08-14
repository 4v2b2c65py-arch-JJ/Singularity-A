#!/usr/bin/env python3
"""
QB Protocol - VR Warp Proximity Guard
Keeps proximity close without causing destruction.
"""

import os
import time
import uuid
import json
import logging
import threading
import math
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.warp.proximity")


@dataclass
class ProximityState:
    state_id: str
    warp_id: str
    origin: Dict[str, float]
    target: Dict[str, float]
    current: Dict[str, float]
    distance: float
    safe_distance: float
    destruction_risk: float
    metadata: Dict[str, Any]
    updated_at: str


class ProximityGuard:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "qb_protocol_vr_proximity.json"):
        self.state_path = state_path
        self.states: Dict[str, ProximityState] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("states", {}).items():
                        self.states[sid] = ProximityState(**s)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "states": {sid: asdict(s) for sid, s in self.states.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def enforce_proximity(self, warp_id: str, origin: Dict[str, float], target: Dict[str, float], max_destruction_risk: float = 0.3) -> ProximityState:
        distance = math.sqrt(sum((origin.get(k, 0) - target.get(k, 0)) ** 2 for k in ["x", "y", "z"]))
        safe_distance = distance * 0.8
        destruction_risk = min(distance * 0.05, 1.0)
        current = {
            "x": origin.get("x", 0) + (target.get("x", 0) - origin.get("x", 0)) * 0.5,
            "y": origin.get("y", 0) + (target.get("y", 0) - origin.get("y", 0)) * 0.5,
            "z": origin.get("z", 0) + (target.get("z", 0) - origin.get("z", 0)) * 0.5,
        }

        state = ProximityState(
            state_id=str(uuid.uuid4()),
            warp_id=warp_id,
            origin=origin,
            target=target,
            current=current,
            distance=round(distance, 4),
            safe_distance=round(safe_distance, 4),
            destruction_risk=round(destruction_risk, 4),
            metadata={"max_destruction_risk": max_destruction_risk},
            updated_at=datetime.utcnow().isoformat() + "Z",
        )

        with self._lock:
            self.states[state.state_id] = state
        self._save()
        return state

    def get_state(self, warp_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for state in self.states.values():
                if state.warp_id == warp_id:
                    return asdict(state)
        return None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            recent = list(self.states.values())[-10:]
            avg_risk = sum(s.destruction_risk for s in recent) / len(recent) if recent else 0
            return {
                "total_states": len(self.states),
                "avg_destruction_risk": round(avg_risk, 4),
            }


proximity_guard = ProximityGuard()

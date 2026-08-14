#!/usr/bin/env python3
"""
QB Protocol - VR Warp Engine
Warp calculation, fluctuation estimation, and realm navigation.
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

LOG = logging.getLogger("qb_protocol.vr_quest.warp.engine")


@dataclass
class WarpFluctuation:
    fluctuation_id: str
    warp_id: str
    amplitude: float
    frequency: float
    phase: float
    estimated_damage: float
    stability: float
    metadata: Dict[str, Any]
    measured_at: str


class WarpEngine:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "qb_protocol_vr_warp.json"):
        self.state_path = state_path
        self.warps: Dict[str, Dict[str, Any]] = {}
        self.fluctuations: List[WarpFluctuation] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.warps = data.get("warps", {})
                    self.fluctuations = [WarpFluctuation(**f) for f in data.get("fluctuations", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "warps": self.warps,
                    "fluctuations": [asdict(f) for f in self.fluctuations[-1000:]],
                }, f, indent=2, default=str)
        except Exception:
            pass

    def calculate_warp(self, origin: Dict[str, float], target: Dict[str, float], amplitude: float = 1.0) -> Dict[str, Any]:
        distance = math.sqrt(sum((origin.get(k, 0) - target.get(k, 0)) ** 2 for k in ["x", "y", "z"]))
        fluctuation = self._estimate_fluctuation(distance, amplitude)
        warp_id = str(uuid.uuid4())

        warp = {
            "warp_id": warp_id,
            "origin": origin,
            "target": target,
            "distance": round(distance, 4),
            "amplitude": amplitude,
            "fluctuation": fluctuation,
            "feasible": fluctuation["estimated_damage"] < 0.5,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        with self._lock:
            self.warps[warp_id] = warp
            self.fluctuations.append(WarpFluctuation(
                fluctuation_id=str(uuid.uuid4()),
                warp_id=warp_id,
                amplitude=amplitude,
                frequency=1.0 / max(distance, 0.001),
                phase=0.0,
                estimated_damage=fluctuation["estimated_damage"],
                stability=fluctuation["stability"],
                metadata={"distance": distance},
                measured_at=datetime.utcnow().isoformat() + "Z",
            ))
            if len(self.fluctuations) > 1000:
                self.fluctuations = self.fluctuations[-1000:]
        self._save()
        return warp

    def _estimate_fluctuation(self, distance: float, amplitude: float) -> Dict[str, Any]:
        base_damage = min(distance * 0.1, 1.0)
        amplitude_factor = amplitude * 0.2
        estimated_damage = min(base_damage + amplitude_factor, 1.0)
        stability = max(1.0 - estimated_damage, 0.0)
        return {
            "estimated_damage": round(estimated_damage, 4),
            "stability": round(stability, 4),
            "safe": estimated_damage < 0.5,
        }

    def get_warp(self, warp_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.warps.get(warp_id)

    def get_warps(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.warps.values())[-limit:]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            recent = self.fluctuations[-10:]
            avg_damage = sum(f.estimated_damage for f in recent) / len(recent) if recent else 0
            return {
                "total_warps": len(self.warps),
                "total_fluctuations": len(self.fluctuations),
                "avg_estimated_damage": round(avg_damage, 4),
            }


warp_engine = WarpEngine()

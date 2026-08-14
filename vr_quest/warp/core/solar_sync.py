#!/usr/bin/env python3
"""
QB Protocol - VR Warp Solar Synchronization
Solar cycle synchronization for realm warping.
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

LOG = logging.getLogger("qb_protocol.vr_quest.warp.solar_sync")


@dataclass
class SolarCycle:
    cycle_id: str
    period: float
    phase: float
    amplitude: float
    next_sync: str
    metadata: Dict[str, Any]
    updated_at: str


class SolarSync:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "qb_protocol_vr_solar.json"):
        self.state_path = state_path
        self.cycles: Dict[str, SolarCycle] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for cid, c in data.get("cycles", {}).items():
                        self.cycles[cid] = SolarCycle(**c)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "cycles": {cid: asdict(c) for cid, c in self.cycles.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_cycle(self, period: float = 24.0, amplitude: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> SolarCycle:
        now = datetime.utcnow()
        cycle = SolarCycle(
            cycle_id=str(uuid.uuid4()),
            period=period,
            phase=now.hour / period * 2 * math.pi,
            amplitude=amplitude,
            next_sync=now.isoformat() + "Z",
            metadata=metadata or {},
            updated_at=now.isoformat() + "Z",
        )
        with self._lock:
            self.cycles[cycle.cycle_id] = cycle
        self._save()
        return cycle

    def get_sync_window(self, cycle_id: str) -> Dict[str, Any]:
        with self._lock:
            cycle = self.cycles.get(cycle_id)
            if not cycle:
                return {"error": "cycle_not_found"}
            now = datetime.utcnow()
            current_phase = (now.hour / cycle.period) * 2 * math.pi
            sync_quality = math.cos(current_phase - cycle.phase) * cycle.amplitude
            return {
                "cycle_id": cycle_id,
                "current_phase": round(current_phase, 4),
                "sync_quality": round(sync_quality, 4),
                "next_sync": cycle.next_sync,
            }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_cycles": len(self.cycles),
                "cycles": list(self.cycles.keys()),
            }


solar_sync = SolarSync()

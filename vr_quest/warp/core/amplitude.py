#!/usr/bin/env python3
"""
QB Protocol - VR Warp Amplitude Pack
Amplitude management for warp stabilization.
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

LOG = logging.getLogger("qb_protocol.vr_quest.warp.amplitude")


@dataclass
class AmplitudeState:
    pack_id: str
    warp_id: str
    base_amplitude: float
    current_amplitude: float
    max_amplitude: float
    stability: float
    metadata: Dict[str, Any]
    updated_at: str


class AmplitudePack:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "qb_protocol_vr_amplitude.json"):
        self.state_path = state_path
        self.packs: Dict[str, AmplitudeState] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for pid, p in data.get("packs", {}).items():
                        self.packs[pid] = AmplitudeState(**p)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "packs": {pid: asdict(p) for pid, p in self.packs.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_pack(self, warp_id: str, base_amplitude: float = 1.0, max_amplitude: float = 2.0, metadata: Optional[Dict[str, Any]] = None) -> AmplitudeState:
        pack = AmplitudeState(
            pack_id=str(uuid.uuid4()),
            warp_id=warp_id,
            base_amplitude=base_amplitude,
            current_amplitude=base_amplitude,
            max_amplitude=max_amplitude,
            stability=1.0,
            metadata=metadata or {},
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.packs[pack.pack_id] = pack
        self._save()
        return pack

    def adjust_amplitude(self, pack_id: str, target_amplitude: float) -> AmplitudeState:
        with self._lock:
            pack = self.packs.get(pack_id)
            if not pack:
                raise ValueError("Pack not found")
            pack.current_amplitude = max(0.0, min(target_amplitude, pack.max_amplitude))
            pack.stability = 1.0 - abs(pack.current_amplitude - pack.base_amplitude) / max(pack.max_amplitude, 0.001)
            pack.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return pack

    def get_pack(self, pack_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            pack = self.packs.get(pack_id)
            return asdict(pack) if pack else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            recent = list(self.packs.values())[-10:]
            avg_stability = sum(p.stability for p in recent) / len(recent) if recent else 0
            return {
                "total_packs": len(self.packs),
                "avg_stability": round(avg_stability, 4),
            }


amplitude_pack = AmplitudePack()

#!/usr/bin/env python3
"""
QB Protocol - Tablet of Destinies Oracle
Packaged oracle solutions integrating bow-of-Achilles consciousness loop,
Magi-Zone escape bridge, and brain mesh chain from probe-sequence.
"""

import sys
import time
import uuid
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from qb_protocol.core.daemon import daemon
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon

TABLET_DIR = Path(__file__).resolve().parent.parent.parent / "The-Tablet-of-Destinies-uppi-m-ti"
LOG = logging.getLogger("qb_protocol.oracle")


@dataclass
class OracleReading:
    reading_id: str
    node_id: str
    oracle_type: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    entropy: float
    coherence: float
    reality_tear: float
    timestamp: str


class TabletOfDestiniesOracle:
    def __init__(self, tablet_dir: Path = TABLET_DIR):
        self.tablet_dir = tablet_dir
        self.bow_dir = tablet_dir / "bow-of-Achilles"
        self.probe_dir = tablet_dir / "probe-sequence"
        self.alive_dir = tablet_dir / "alive-eal"
        self.readings: List[OracleReading] = []
        self._lock = threading.RLock()
        self._load_components()

    def _load_components(self):
        self.has_consciousness_loop = False
        self.has_escape_bridge = False
        self.has_brain_mesh = False
        try:
            sys.path.insert(0, str(self.bow_dir))
            from consciousness_loop import ConsciousnessLoop
            self.consciousness_loop = ConsciousnessLoop()
            self.has_consciousness_loop = True
            LOG.info("Loaded bow-of-Achilles consciousness loop")
        except Exception as e:
            LOG.warning("Consciousness loop not loaded: %s", e)
            self.consciousness_loop = None

        try:
            sys.path.insert(0, str(self.bow_dir))
            from conscience_escape_bridge import run_magi_escape, EscapePayload
            self.run_magi_escape = run_magi_escape
            self.EscapePayload = EscapePayload
            self.has_escape_bridge = True
            LOG.info("Loaded conscience escape bridge")
        except Exception as e:
            LOG.warning("Escape bridge not loaded: %s", e)
            self.run_magi_escape = None

        try:
            sys.path.insert(0, str(self.probe_dir))
            from brain_mesh_chain import BrainMeshChain
            self.brain_mesh = BrainMeshChain()
            self.has_brain_mesh = True
            LOG.info("Loaded brain mesh chain")
        except Exception as e:
            LOG.warning("Brain mesh chain not loaded: %s", e)
            self.brain_mesh = None

    def query_consciousness(self, prompt: str, max_iterations: int = 10) -> Dict[str, Any]:
        if not self.has_consciousness_loop:
            return {"error": "consciousness_loop_unavailable", "prompt": prompt}
        try:
            result = self.consciousness_loop.run(prompt, max_iterations=max_iterations)
            return {
                "prompt": prompt,
                "result": result,
                "oracle_type": "consciousness_loop",
            }
        except Exception as e:
            return {"error": str(e), "oracle_type": "consciousness_loop"}

    def run_magi_zone(self, voice_phrases: List[str], origin3d: List[float], movement_vector: List[float], in_danger: bool = True, default_tier: int = 2) -> Dict[str, Any]:
        if not self.has_escape_bridge:
            return {"error": "escape_bridge_unavailable"}
        try:
            payload = self.run_magi_escape(
                voice_phrases=voice_phrases,
                origin3d=tuple(origin3d),
                movement_vector=tuple(movement_vector),
                in_danger=in_danger,
                default_tier=default_tier,
            )
            return {
                "oracle_type": "magi_zone",
                "waveState": payload.waveState,
                "enforceResult": {
                    "realityTear": payload.enforceResult.get("realityTear") if payload.enforceResult else None,
                    "dimensionalState": payload.enforceResult.get("dimensionalState") if payload.enforceResult else None,
                },
                "zoneMap3D": payload.zoneMap3D,
                "tier": payload.tier,
                "permitted": payload.permitted,
                "executed": payload.executed,
            }
        except Exception as e:
            return {"error": str(e), "oracle_type": "magi_zone"}

    def read_brain_mesh(self) -> Dict[str, Any]:
        if not self.has_brain_mesh:
            return {"error": "brain_mesh_unavailable"}
        try:
            state = self.brain_mesh._state
            return {
                "oracle_type": "brain_mesh",
                "chain_length": state.get("chain_length"),
                "highest_bound": state.get("highest_bound"),
                "total_raw_rf_entries": state.get("total_raw_rf_entries"),
                "active_weight": state.get("active_weight"),
                "neural_nets_count": len(state.get("neural_nets", {})),
            }
        except Exception as e:
            return {"error": str(e), "oracle_type": "brain_mesh"}

    def record_reading(self, oracle_type: str, input_data: Dict[str, Any], output_data: Dict[str, Any], entropy: float = 0.0, coherence: float = 0.0, reality_tear: float = 0.0):
        reading = OracleReading(
            reading_id=str(uuid.uuid4()),
            node_id=daemon.node_id,
            oracle_type=oracle_type,
            input_data=input_data,
            output_data=output_data,
            entropy=entropy,
            coherence=coherence,
            reality_tear=reality_tear,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.readings.append(reading)
            if len(self.readings) > 10000:
                self.readings = self.readings[-10000:]
        return reading

    def get_status(self) -> Dict[str, Any]:
        return {
            "tablet_dir": str(self.tablet_dir),
            "consciousness_loop": self.has_consciousness_loop,
            "escape_bridge": self.has_escape_bridge,
            "brain_mesh": self.has_brain_mesh,
            "reading_count": len(self.readings),
        }


tablet_oracle = TabletOfDestiniesOracle()

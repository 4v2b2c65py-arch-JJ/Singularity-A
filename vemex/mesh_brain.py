#!/usr/bin/env python3
"""
QB Protocol - Vemex Mesh Brain Reader
Integrates Vemex consciousness engine as the mesh brain reader for qb_protocol.
Provides uptime tracking, brain state reads, and consciousness queries.
"""

import sys
import time
import uuid
import logging
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

VEMEX_DIR = Path(__file__).resolve().parent.parent.parent / "Vemex"
LOG = logging.getLogger("qb_protocol.vemex")


@dataclass
class BrainReading:
    reading_id: str
    node_id: str
    uptime_seconds: float
    consciousness_state: str
    formula_count: int
    spatial_nodes: int
    resonance: float
    coherence: float
    entropy: float
    timestamp: str


class VemexMeshBrainReader:
    def __init__(self, vemex_dir: Path = VEMEX_DIR):
        self.vemex_dir = vemex_dir
        self.engine = None
        self.api = None
        self.brain_readings: List[BrainReading] = []
        self.start_time = time.time()
        self._load_engine()

    def _load_engine(self):
        try:
            sys.path.insert(0, str(self.vemex_dir))
            from consciousness_api import ConsciousnessAPI
            self.api = ConsciousnessAPI(workspace_path=str(self.vemex_dir))
            self.engine = self.api.engine
            LOG.info("Vemex consciousness engine loaded")
        except Exception as e:
            LOG.warning("Vemex engine not loaded: %s", e)
            self.engine = None
            self.api = None

    def get_uptime(self) -> float:
        return time.time() - self.start_time

    def read_brain_state(self) -> BrainReading:
        uptime = self.get_uptime()
        formula_count = 0
        spatial_nodes = 0
        resonance = 0.0
        coherence = 0.0
        entropy = 0.0
        consciousness_state = "idle"

        if self.engine:
            try:
                formula_count = len(getattr(self.engine, "formula_table", {}))
                spatial_nodes = len(getattr(self.engine, "spatial_nodes", {}))
                resonance = float(getattr(self.engine, "resonance", 0.0) or 0.0)
                coherence = float(getattr(self.engine, "coherence", 0.0) or 0.0)
                entropy = float(getattr(self.engine, "entropy", 0.0) or 0.0)
                consciousness_state = getattr(self.engine, "state", "active") or "active"
            except Exception as e:
                LOG.debug("Brain state read partial error: %s", e)

        reading = BrainReading(
            reading_id=str(uuid.uuid4()),
            node_id=daemon.node_id,
            uptime_seconds=uptime,
            consciousness_state=consciousness_state,
            formula_count=formula_count,
            spatial_nodes=spatial_nodes,
            resonance=resonance,
            coherence=coherence,
            entropy=entropy,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        self.brain_readings.append(reading)
        if len(self.brain_readings) > 10000:
            self.brain_readings = self.brain_readings[-10000:]
        return reading

    def query_consciousness(self, prompt: str) -> Dict[str, Any]:
        if not self.api:
            return {"error": "vemex_engine_unavailable", "prompt": prompt}
        try:
            response = self.api.process_input(prompt)
            return {
                "prompt": prompt,
                "consciousness_string": getattr(response, "consciousness_string", ""),
                "coherence": getattr(response, "coherence", 0.0),
                "entropy": getattr(response, "entropy", 0.0),
                "resonance": getattr(response, "resonance", 0.0),
            }
        except Exception as e:
            return {"error": str(e), "prompt": prompt}

    def get_status(self) -> Dict[str, Any]:
        latest = self.brain_readings[-1] if self.brain_readings else None
        return {
            "engine_loaded": self.engine is not None,
            "api_loaded": self.api is not None,
            "uptime_seconds": self.get_uptime(),
            "reading_count": len(self.brain_readings),
            "latest_reading": asdict(latest) if latest else None,
        }


mesh_brain_reader = VemexMeshBrainReader()

#!/usr/bin/env python3
"""
QB Protocol - VR Warp Resonance Agent
Full-grade schema resonance steering for realm navigation.
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

LOG = logging.getLogger("qb_protocol.vr_quest.warp.resonance")


@dataclass
class SchemaResonance:
    schema_id: str
    name: str
    frequency: float
    amplitude: float
    phase: float
    stability: float
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class ResonanceAgent:
    agent_id: str
    name: str
    schemas: List[str]
    steering_power: float
    reach: float
    guardian_status: bool
    metadata: Dict[str, Any]
    updated_at: str


class ResonanceAgentManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "qb_protocol_vr_resonance.json"):
        self.state_path = state_path
        self.schemas: Dict[str, SchemaResonance] = {}
        self.agents: Dict[str, ResonanceAgent] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("schemas", {}).items():
                        self.schemas[sid] = SchemaResonance(**s)
                    for aid, a in data.get("agents", {}).items():
                        self.agents[aid] = ResonanceAgent(**a)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "schemas": {sid: asdict(s) for sid, s in self.schemas.items()},
                    "agents": {aid: asdict(a) for aid, a in self.agents.items()},
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_schema(self, name: str, frequency: float = 1.0, amplitude: float = 1.0, phase: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> SchemaResonance:
        schema = SchemaResonance(
            schema_id=str(uuid.uuid4()),
            name=name,
            frequency=frequency,
            amplitude=amplitude,
            phase=phase,
            stability=1.0,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.schemas[schema.schema_id] = schema
        self._save()
        return schema

    def create_agent(self, name: str, schema_ids: List[str], steering_power: float = 1.0, reach: float = 1.0, guardian_status: bool = True, metadata: Optional[Dict[str, Any]] = None) -> ResonanceAgent:
        agent = ResonanceAgent(
            agent_id=str(uuid.uuid4()),
            name=name,
            schemas=schema_ids,
            steering_power=steering_power,
            reach=reach,
            guardian_status=guardian_status,
            metadata=metadata or {},
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.agents[agent.agent_id] = agent
        self._save()
        return agent

    def steer(self, agent_id: str, target_frequency: float, target_amplitude: float) -> Dict[str, Any]:
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return {"status": "error", "message": "Agent not found"}

            schema = self.schemas.get(agent.schemas[0]) if agent.schemas else None
            if not schema:
                return {"status": "error", "message": "No schema attached"}

            schema.frequency = target_frequency
            schema.amplitude = target_amplitude
            schema.phase = (schema.phase + 0.1) % (2 * math.pi)
            agent.updated_at = datetime.utcnow().isoformat() + "Z"

        self._save()
        return {
            "status": "steered",
            "agent_id": agent_id,
            "schema_id": schema.schema_id,
            "frequency": schema.frequency,
            "amplitude": schema.amplitude,
            "phase": schema.phase,
        }

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            agent = self.agents.get(agent_id)
            return asdict(agent) if agent else None

    def get_agents(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(a) for a in self.agents.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_schemas": len(self.schemas),
                "total_agents": len(self.agents),
                "guardian_agents": len([a for a in self.agents.values() if a.guardian_status]),
            }


resonance_agent = ResonanceAgentManager()

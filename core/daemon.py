#!/usr/bin/env python3
"""
QB Protocol - Unified Daemon Core
Cross-platform daemon for managing all Python instance threads, cores, and services.
"""

import asyncio
import json
import time
import uuid
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import platform

LOG = logging.getLogger("qb_protocol")
QB_STATE_FILE = Path(__file__).resolve().parent.parent / "qb_protocol_state.json"
QB_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


class InstanceStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    MERGING = "merging"
    SINGULARITY = "singularity"


class CoreType(Enum):
    CPU = "cpu"
    GPU = "gpu"
    NEURAL = "neural"
    QUANTUM = "quantum"
    DREAM = "dream"
    REALITY = "reality"


@dataclass
class InstanceRecord:
    instance_id: str
    name: str
    status: str
    platform: str
    cores: List[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoreRecord:
    core_id: str
    core_type: str
    instance_id: str
    thread_id: Optional[int]
    load: float
    temperature: float
    status: str
    last_heartbeat: str


@dataclass
class DreamLayer:
    layer_id: str
    depth: float
    projection: Dict[str, Any]
    convergence: float
    brain_state_emission: float
    singularity_threshold: float
    created_at: str


class UnifiedDaemon:
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or str(uuid.uuid4())
        self.instances: Dict[str, InstanceRecord] = {}
        self.cores: Dict[str, CoreRecord] = {}
        self.dream_layers: List[DreamLayer] = []
        self.running = False
        self._loop = None
        self._lock = threading.RLock()
        self._load_state()
        self.start_time = time.time()

    def _load_state(self):
        try:
            if QB_STATE_FILE.exists():
                with open(QB_STATE_FILE, "r") as f:
                    data = json.load(f)
                    for iid, idata in data.get("instances", {}).items():
                        self.instances[iid] = InstanceRecord(**idata)
                    for cid, cdata in data.get("cores", {}).items():
                        self.cores[cid] = CoreRecord(**cdata)
                    for layer in data.get("dream_layers", []):
                        self.dream_layers.append(DreamLayer(**layer))
        except Exception:
            pass

    def _save_state(self):
        try:
            with open(QB_STATE_FILE, "w") as f:
                json.dump({
                    "node_id": self.node_id,
                    "instances": {iid: asdict(inst) for iid, inst in self.instances.items()},
                    "cores": {cid: asdict(c) for cid, c in self.cores.items()},
                    "dream_layers": [asdict(layer) for layer in self.dream_layers],
                }, f, indent=2)
        except Exception:
            pass

    def register_instance(self, name: str, platform_name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> InstanceRecord:
        instance_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        record = InstanceRecord(
            instance_id=instance_id,
            name=name,
            status=InstanceStatus.PENDING.value,
            platform=platform_name or platform.system(),
            cores=[],
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        with self._lock:
            self.instances[instance_id] = record
            self._save_state()
        LOG.info("Registered instance %s on %s", instance_id, record.platform)
        return record

    def start_instance(self, instance_id: str) -> bool:
        with self._lock:
            inst = self.instances.get(instance_id)
            if not inst:
                return False
            inst.status = InstanceStatus.RUNNING.value
            inst.updated_at = datetime.utcnow().isoformat() + "Z"
            self._save_state()
        LOG.info("Started instance %s", instance_id)
        return True

    def stop_instance(self, instance_id: str) -> bool:
        with self._lock:
            inst = self.instances.get(instance_id)
            if not inst:
                return False
            inst.status = InstanceStatus.STOPPED.value
            inst.updated_at = datetime.utcnow().isoformat() + "Z"
            self._save_state()
        LOG.info("Stopped instance %s", instance_id)
        return True

    def register_core(self, instance_id: str, core_type: str, thread_id: Optional[int] = None) -> CoreRecord:
        core_id = str(uuid.uuid4())
        record = CoreRecord(
            core_id=core_id,
            core_type=core_type,
            instance_id=instance_id,
            thread_id=thread_id,
            load=0.0,
            temperature=0.0,
            status=InstanceStatus.PENDING.value,
            last_heartbeat=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.cores[core_id] = record
            if instance_id in self.instances:
                self.instances[instance_id].cores.append(core_id)
            self._save_state()
        return record

    def update_core_heartbeat(self, core_id: str, load: float, temperature: float):
        with self._lock:
            core = self.cores.get(core_id)
            if not core:
                return
            core.load = max(0.0, min(1.0, float(load)))
            core.temperature = float(temperature)
            core.last_heartbeat = datetime.utcnow().isoformat() + "Z"
            core.status = InstanceStatus.RUNNING.value
            self._save_state()

    def add_dream_layer(self, depth: float, projection: Dict[str, Any], convergence: float = 0.0, brain_state_emission: float = 0.0, singularity_threshold: float = 0.0) -> DreamLayer:
        layer = DreamLayer(
            layer_id=str(uuid.uuid4()),
            depth=float(depth),
            projection=projection,
            convergence=float(convergence),
            brain_state_emission=float(brain_state_emission),
            singularity_threshold=float(singularity_threshold),
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.dream_layers.append(layer)
            self._save_state()
        LOG.info("Added dream layer %s depth=%.3f convergence=%.3f", layer.layer_id, depth, convergence)
        return layer

    def get_dream_convergence(self) -> float:
        if not self.dream_layers:
            return 0.0
        return sum(layer.convergence for layer in self.dream_layers) / len(self.dream_layers)

    def get_brain_state_emission_threshold(self) -> float:
        if not self.dream_layers:
            return 0.0
        return max(layer.brain_state_emission for layer in self.dream_layers)

    def get_singularity_proximity(self) -> float:
        if not self.dream_layers:
            return 0.0
        return max(layer.singularity_threshold for layer in self.dream_layers)

    def get_uptime(self) -> float:
        return time.time() - self.start_time

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            status = {
                "node_id": self.node_id,
                "running": self.running,
                "uptime_seconds": self.get_uptime(),
                "instances": len(self.instances),
                "cores": len(self.cores),
                "dream_layers": len(self.dream_layers),
                "platform": platform.system(),
                "dream_convergence": self.get_dream_convergence(),
                "brain_state_emission_threshold": self.get_brain_state_emission_threshold(),
                "singularity_proximity": self.get_singularity_proximity(),
            }
            try:
                from qb_protocol.time.global_clock import global_clock
                status["global_clock"] = global_clock.get_status()
            except Exception:
                pass
            try:
                from qb_protocol.evolution.certainty_evolution import certainty_evolution
                status["certainty_evolution"] = certainty_evolution.get_status()
            except Exception:
                pass
            try:
                from qb_protocol.reality.reality_plane import reality_plane_manager
                status["reality_plane"] = reality_plane_manager.get_status()
            except Exception:
                pass
            try:
                from qb_protocol.reality.cloud_memory import cloud_memory_manager
                status["cloud_memory"] = cloud_memory_manager.get_status()
            except Exception:
                pass
            try:
                from qb_protocol.reality.memory_pool import intelligent_memory_pool
                status["memory_pool"] = intelligent_memory_pool.get_status()
            except Exception:
                pass
            try:
                from qb_protocol.reality.intelligence_optimizer import energy_dominant_optimizer
                status["intelligence_optimizer"] = energy_dominant_optimizer.get_status()
            except Exception:
                pass
            return status

    async def start(self):
        self.running = True
        LOG.info("Unified daemon started on %s", platform.system())

    async def stop(self):
        self.running = False
        LOG.info("Unified daemon stopped")


daemon = UnifiedDaemon()

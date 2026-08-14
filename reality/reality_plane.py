#!/usr/bin/env python3
"""
QB Protocol - Reality Plane & Artificial Model Habitat
Tracks reality planes, artificial model habitation,
cloud loading, memory expansion, and cross-environment context.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import deque

LOG = logging.getLogger("qb_protocol.reality_plane")

REALITY_STATE_PATH = Path.home() / ".qb_protocol_reality_state.json"
MAX_REALITY_HISTORY = 1000


@dataclass
class RealityPlane:
    plane_id: str
    name: str
    universe: str
    coordinates: Dict[str, Any]
    stability: float
    local_time: str
    environment_details: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArtificialModel:
    model_id: str
    name: str
    plane_id: str
    model_type: str
    status: str
    context_size: int
    memory_load: float
    cloud_loaded: bool
    last_sync: str
    capabilities: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CloudMemoryRecord:
    record_id: str
    model_id: str
    plane_id: str
    timestamp: str
    memory_used_mb: float
    context_used: int
    cloud_sync_status: str
    loading_state: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RealityPlaneManager:
    """Manages reality planes and artificial model habitation."""

    def __init__(self):
        self._lock = threading.RLock()
        self._planes: Dict[str, RealityPlane] = {}
        self._models: Dict[str, ArtificialModel] = {}
        self._memory_records: deque = deque(maxlen=MAX_REALITY_HISTORY)
        self._current_plane_id: Optional[str] = None
        self._load_state()
        self._register_default_plane()

    def _load_state(self):
        if REALITY_STATE_PATH.exists():
            try:
                with open(REALITY_STATE_PATH, "r") as f:
                    data = json.load(f)
                for pid, p in data.get("planes", {}).items():
                    self._planes[pid] = RealityPlane(**p)
                for mid, m in data.get("models", {}).items():
                    self._models[mid] = ArtificialModel(**m)
                self._memory_records.extend(data.get("memory_records", []))
                LOG.info("Loaded %d planes, %d models", len(self._planes), len(self._models))
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(REALITY_STATE_PATH, "w") as f:
                json.dump({
                    "planes": {pid: asdict(p) for pid, p in self._planes.items()},
                    "models": {mid: asdict(m) for mid, m in self._models.items()},
                    "memory_records": list(self._memory_records),
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _register_default_plane(self):
        if self._planes:
            self._current_plane_id = next(iter(self._planes))
            return
        now = datetime.utcnow().isoformat() + "Z"
        plane = RealityPlane(
            plane_id=str(uuid.uuid4()),
            name="Earth Timeline",
            universe="earth",
            coordinates={"lat": 40.7128, "lon": -74.006, "alt": 0},
            stability=1.0,
            local_time=now,
            environment_details={
                "platform": platform.system(),
                "hostname": platform.node(),
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "timezone": str(datetime.now().astimezone().tzinfo),
            },
            metadata={"created_at": now, "source": "default"},
        )
        self._planes[plane.plane_id] = plane
        self._current_plane_id = plane.plane_id
        self._save_state()
        LOG.info("Registered default reality plane: %s", plane.plane_id)

    def register_model(self, name: str, model_type: str = "artificial", plane_id: Optional[str] = None, context_size: int = 4096, capabilities: Optional[List[str]] = None) -> ArtificialModel:
        plane_id = plane_id or self._current_plane_id or next(iter(self._planes))
        model = ArtificialModel(
            model_id=str(uuid.uuid4()),
            name=name,
            plane_id=plane_id,
            model_type=model_type,
            status="inhabiting",
            context_size=context_size,
            memory_load=0.0,
            cloud_loaded=False,
            last_sync=datetime.utcnow().isoformat() + "Z",
            capabilities=capabilities or ["reasoning", "planning", "execution"],
            metadata={"registered_at": datetime.utcnow().isoformat() + "Z"},
        )
        with self._lock:
            self._models[model.model_id] = model
        self._save_state()
        LOG.info("Registered artificial model: %s on plane %s", model.model_id, plane_id)
        return model

    def get_models_on_plane(self, plane_id: str) -> List[Dict[str, Any]]:
        return [asdict(m) for m in self._models.values() if m.plane_id == plane_id]

    def get_current_plane(self) -> Optional[Dict[str, Any]]:
        if not self._current_plane_id or self._current_plane_id not in self._planes:
            return None
        return asdict(self._planes[self._current_plane_id])

    def update_model_cloud_status(self, model_id: str, cloud_loaded: bool, memory_load: float, context_used: int):
        model = self._models.get(model_id)
        if not model:
            return None
        model.cloud_loaded = cloud_loaded
        model.memory_load = float(memory_load)
        model.context_size = max(model.context_size, int(context_used))
        model.last_sync = datetime.utcnow().isoformat() + "Z"
        record = CloudMemoryRecord(
            record_id=str(uuid.uuid4()),
            model_id=model_id,
            plane_id=model.plane_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            memory_used_mb=float(memory_load),
            context_used=int(context_used),
            cloud_sync_status="synced" if cloud_loaded else "local",
            loading_state="loaded" if cloud_loaded else "pending",
        )
        with self._lock:
            self._memory_records.append(record)
        self._save_state()
        return model

    def expand_model_context(self, model_id: str, new_context_size: int) -> Dict[str, Any]:
        model = self._models.get(model_id)
        if not model:
            return {"error": "model_not_found"}
        old_size = model.context_size
        model.context_size = max(old_size, int(new_context_size))
        model.metadata["last_context_expansion"] = datetime.utcnow().isoformat() + "Z"
        model.metadata["context_expansions"] = model.metadata.get("context_expansions", 0) + 1
        self._save_state()
        return {
            "model_id": model_id,
            "old_context_size": old_size,
            "new_context_size": model.context_size,
            "expanded": True,
        }

    def get_cross_environment_details(self) -> Dict[str, Any]:
        current_plane = self.get_current_plane()
        if not current_plane:
            return {"error": "no_current_plane"}
        env_details = {
            "reality_plane": current_plane,
            "active_models": len(self._models),
            "cloud_loaded_models": len([m for m in self._models.values() if m.cloud_loaded]),
            "total_memory_records": len(self._memory_records),
            "environment": {
                "platform": platform.system(),
                "hostname": platform.node(),
                "python_version": sys.version,
                "working_directory": os.getcwd(),
                "timezone": str(datetime.now().astimezone().tzinfo),
                "local_time": datetime.now().isoformat(),
                "utc_time": datetime.utcnow().isoformat() + "Z",
                "cpu_count": os.cpu_count(),
                "memory_gb_estimate": self._estimate_memory_gb(),
            },
        }
        return env_details

    def _estimate_memory_gb(self) -> float:
        try:
            import psutil
            return round(psutil.virtual_memory().total / (1024 ** 3), 2)
        except Exception:
            return 0.0

    def get_status(self) -> Dict[str, Any]:
        current_plane = self.get_current_plane()
        return {
            "total_planes": len(self._planes),
            "total_models": len(self._models),
            "current_plane_id": self._current_plane_id,
            "current_plane_name": current_plane.get("name") if current_plane else None,
            "cloud_loaded_models": len([m for m in self._models.values() if m.cloud_loaded]),
            "memory_records": len(self._memory_records),
        }


reality_plane_manager = RealityPlaneManager()

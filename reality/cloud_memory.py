#!/usr/bin/env python3
"""
QB Protocol - Cloud Loading & Memory Expansion
Manages cloud model loading, memory expansion,
higher context sizes, and cross-environment model support.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import deque

LOG = logging.getLogger("qb_protocol.cloud_memory")

CLOUD_STATE_PATH = Path.home() / ".qb_protocol_cloud_memory.json"
MAX_CLOUD_HISTORY = 1000


@dataclass
class CloudModelRecord:
    record_id: str
    model_id: str
    model_name: str
    model_type: str
    context_size: int
    memory_allocated_mb: float
    cloud_provider: Optional[str]
    loaded_at: str
    last_accessed: str
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryExpansion:
    expansion_id: str
    model_id: str
    from_context_size: int
    to_context_size: int
    memory_increase_mb: float
    triggered_by: str
    timestamp: str


class CloudMemoryManager:
    """Manages cloud loading and memory expansion for artificial models."""

    def __init__(self):
        self._lock = threading.RLock()
        self._cloud_models: Dict[str, CloudModelRecord] = {}
        self._expansions: deque = deque(maxlen=MAX_CLOUD_HISTORY)
        self._load_state()

    def _load_state(self):
        if CLOUD_STATE_PATH.exists():
            try:
                with open(CLOUD_STATE_PATH, "r") as f:
                    data = json.load(f)
                for rid, r in data.get("cloud_models", {}).items():
                    self._cloud_models[rid] = CloudModelRecord(**r)
                for exp in data.get("expansions", []):
                    self._expansions.append(MemoryExpansion(**exp))
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(CLOUD_STATE_PATH, "w") as f:
                json.dump({
                    "cloud_models": {rid: asdict(r) for rid, r in self._cloud_models.items()},
                    "expansions": [asdict(e) for e in self._expansions],
                }, f, indent=2, default=str)
        except Exception:
            pass

    def load_model_to_cloud(self, model_id: str, model_name: str, model_type: str = "artificial", context_size: int = 4096, cloud_provider: Optional[str] = None, memory_mb: float = 512.0) -> CloudModelRecord:
        record = CloudModelRecord(
            record_id=str(uuid.uuid4()),
            model_id=model_id,
            model_name=model_name,
            model_type=model_type,
            context_size=int(context_size),
            memory_allocated_mb=float(memory_mb),
            cloud_provider=cloud_provider,
            loaded_at=datetime.utcnow().isoformat() + "Z",
            last_accessed=datetime.utcnow().isoformat() + "Z",
            status="loaded",
            metadata={"loaded_by": "cloud_memory_manager"},
        )
        with self._lock:
            self._cloud_models[model_id] = record
        self._save_state()
        LOG.info("Loaded model to cloud: %s context=%d memory=%.1fMB", model_name, context_size, memory_mb)
        return record

    def expand_model_memory(self, model_id: str, new_context_size: int, trigger: str = "auto") -> Dict[str, Any]:
        model = self._cloud_models.get(model_id)
        if not model:
            return {"error": "model_not_cloud_loaded", "model_id": model_id}
        old_size = model.context_size
        increase = max(0, int(new_context_size) - old_size)
        memory_increase_mb = (increase / 4096.0) * 512.0
        expansion = MemoryExpansion(
            expansion_id=str(uuid.uuid4()),
            model_id=model_id,
            from_context_size=old_size,
            to_context_size=int(new_context_size),
            memory_increase_mb=round(memory_increase_mb, 2),
            triggered_by=trigger,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self._expansions.append(expansion)
            model.context_size = int(new_context_size)
            model.memory_allocated_mb += memory_increase_mb
            model.last_accessed = datetime.utcnow().isoformat() + "Z"
        self._save_state()
        return {
            "model_id": model_id,
            "from_context_size": old_size,
            "to_context_size": model.context_size,
            "memory_increase_mb": round(memory_increase_mb, 2),
            "trigger": trigger,
        }

    def get_model_status(self, model_id: str) -> Dict[str, Any]:
        model = self._cloud_models.get(model_id)
        if not model:
            return {"error": "model_not_found"}
        return asdict(model)

    def get_all_models(self) -> List[Dict[str, Any]]:
        return [asdict(m) for m in self._cloud_models.values()]

    def get_expansion_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [asdict(e) for e in list(self._expansions)[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_cloud_models": len(self._cloud_models),
            "total_expansions": len(self._expansions),
            "models": [asdict(m) for m in self._cloud_models.values()],
        }


cloud_memory_manager = CloudMemoryManager()

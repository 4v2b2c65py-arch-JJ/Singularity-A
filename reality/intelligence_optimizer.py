#!/usr/bin/env python3
"""
QB Protocol - Energy-Dominant Intelligence Optimizer
Optimizes intelligence processing for energy efficiency.
Smart massless processing with amassed reserve pooling.
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

LOG = logging.getLogger("qb_protocol.intelligence_optimizer")

OPTIMIZER_STATE_PATH = Path.home() / ".qb_protocol_intelligence_optimizer.json"
MAX_OPTIMIZER_HISTORY = 1000


@dataclass
class IntelligenceTask:
    task_id: str
    model_id: str
    task_type: str
    energy_cost: float
    memory_cost_mb: float
    estimated_duration_ms: float
    priority: int
    status: str
    created_at: str
    completed_at: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationProfile:
    profile_id: str
    name: str
    energy_efficiency_target: float
    memory_reserve_mb: float
    context_size: int
    batch_size: int
    active: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnergyDominantIntelligenceOptimizer:
    """Optimizes intelligence for energy efficiency with smart massless processing."""

    def __init__(self):
        self._lock = threading.RLock()
        self._tasks: Dict[str, IntelligenceTask] = {}
        self._profiles: Dict[str, OptimizationProfile] = {}
        self._task_history: deque = deque(maxlen=MAX_OPTIMIZER_HISTORY)
        self._current_profile_id: Optional[str] = None
        self._energy_saved_total: float = 0.0
        self._memory_saved_total_mb: float = 0.0
        self._load_state()
        self._register_default_profile()

    def _load_state(self):
        if OPTIMIZER_STATE_PATH.exists():
            try:
                with open(OPTIMIZER_STATE_PATH, "r") as f:
                    data = json.load(f)
                for tid, t in data.get("tasks", {}).items():
                    self._tasks[tid] = IntelligenceTask(**t)
                for pid, p in data.get("profiles", {}).items():
                    self._profiles[pid] = OptimizationProfile(**p)
                self._task_history.extend(data.get("task_history", []))
                self._energy_saved_total = data.get("energy_saved_total", 0.0)
                self._memory_saved_total_mb = data.get("memory_saved_total_mb", 0.0)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(OPTIMIZER_STATE_PATH, "w") as f:
                json.dump({
                    "tasks": {tid: asdict(t) for tid, t in self._tasks.items()},
                    "profiles": {pid: asdict(p) for pid, p in self._profiles.items()},
                    "task_history": list(self._task_history),
                    "energy_saved_total": self._energy_saved_total,
                    "memory_saved_total_mb": self._memory_saved_total_mb,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _register_default_profile(self):
        if self._profiles:
            self._current_profile_id = next(iter(self._profiles))
            return
        profile = OptimizationProfile(
            profile_id=str(uuid.uuid4()),
            name="energy_dominant_default",
            energy_efficiency_target=0.85,
            memory_reserve_mb=4096.0,
            context_size=65536,
            batch_size=8,
            active=True,
            metadata={"created_at": datetime.utcnow().isoformat() + "Z", "source": "default"},
        )
        self._profiles[profile.profile_id] = profile
        self._current_profile_id = profile.profile_id
        self._save_state()

    def create_profile(self, name: str, energy_efficiency_target: float = 0.85, memory_reserve_mb: float = 4096.0, context_size: int = 65536, batch_size: int = 8) -> OptimizationProfile:
        profile = OptimizationProfile(
            profile_id=str(uuid.uuid4()),
            name=name,
            energy_efficiency_target=float(energy_efficiency_target),
            memory_reserve_mb=float(memory_reserve_mb),
            context_size=int(context_size),
            batch_size=int(batch_size),
            active=True,
            metadata={"created_at": datetime.utcnow().isoformat() + "Z"},
        )
        with self._lock:
            self._profiles[profile.profile_id] = profile
            self._current_profile_id = profile.profile_id
        self._save_state()
        LOG.info("Created optimization profile: %s efficiency=%.2f", name, energy_efficiency_target)
        return profile

    def submit_task(self, model_id: str, task_type: str, memory_cost_mb: float, estimated_duration_ms: float, priority: int = 5) -> IntelligenceTask:
        profile = self._profiles.get(self._current_profile_id) if self._current_profile_id else None
        energy_cost = memory_cost_mb * estimated_duration_ms / 1000.0
        if profile:
            energy_cost *= (1.0 - profile.energy_efficiency_target)
        task = IntelligenceTask(
            task_id=str(uuid.uuid4()),
            model_id=model_id,
            task_type=task_type,
            energy_cost=round(energy_cost, 6),
            memory_cost_mb=float(memory_cost_mb),
            estimated_duration_ms=float(estimated_duration_ms),
            priority=priority,
            status="queued",
            created_at=datetime.utcnow().isoformat() + "Z",
            completed_at=None,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        self._save_state()
        return task

    def complete_task(self, task_id: str, actual_duration_ms: float) -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            return {"error": "task_not_found"}
        task.status = "completed"
        task.completed_at = datetime.utcnow().isoformat() + "Z"
        estimated = task.estimated_duration_ms
        efficiency_gain = max(0.0, estimated - actual_duration_ms) / max(estimated, 1.0)
        energy_saved = task.energy_cost * efficiency_gain
        memory_saved = task.memory_cost_mb * efficiency_gain * 0.1
        with self._lock:
            self._energy_saved_total += energy_saved
            self._memory_saved_total_mb += memory_saved
            self._task_history.append({
                "task_id": task_id,
                "model_id": task.model_id,
                "task_type": task.task_type,
                "efficiency_gain": round(efficiency_gain, 4),
                "energy_saved": round(energy_saved, 6),
                "memory_saved_mb": round(memory_saved, 4),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
        self._save_state()
        return {
            "task_id": task_id,
            "status": "completed",
            "efficiency_gain": round(efficiency_gain, 4),
            "energy_saved": round(energy_saved, 6),
            "memory_saved_mb": round(memory_saved, 4),
        }

    def get_optimization_stats(self) -> Dict[str, Any]:
        profile = self._profiles.get(self._current_profile_id) if self._current_profile_id else None
        recent_tasks = list(self._task_history)[-100:]
        avg_efficiency = sum(t["efficiency_gain"] for t in recent_tasks) / max(len(recent_tasks), 1) if recent_tasks else 0.0
        return {
            "total_tasks": len(self._tasks),
            "completed_tasks": len([t for t in self._tasks.values() if t.status == "completed"]),
            "queued_tasks": len([t for t in self._tasks.values() if t.status == "queued"]),
            "current_profile": asdict(profile) if profile else None,
            "energy_saved_total": round(self._energy_saved_total, 6),
            "memory_saved_total_mb": round(self._memory_saved_total_mb, 2),
            "average_efficiency_gain": round(avg_efficiency, 4),
            "recent_task_count": len(recent_tasks),
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_profiles": len(self._profiles),
            "total_tasks": len(self._tasks),
            "current_profile_id": self._current_profile_id,
            "energy_saved_total": round(self._energy_saved_total, 6),
            "memory_saved_total_mb": round(self._memory_saved_total_mb, 2),
        }


energy_dominant_optimizer = EnergyDominantIntelligenceOptimizer()

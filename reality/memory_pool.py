#!/usr/bin/env python3
"""
QB Protocol - Intelligent Memory Pool & Reserve System
Amassed reserved pooling for energy-dominant intelligence.
Optimizes RAM usage with smart massless allocation.
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

LOG = logging.getLogger("qb_protocol.memory_pool")

MEMORY_STATE_PATH = Path.home() / ".qb_protocol_memory_pool.json"
MAX_MEMORY_HISTORY = 1000


@dataclass
class MemoryPool:
    pool_id: str
    name: str
    reserved_mb: float
    allocated_mb: float
    available_mb: float
    energy_efficiency: float
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryReservation:
    reservation_id: str
    pool_id: str
    model_id: str
    reserved_mb: float
    allocated_mb: float
    priority: int
    energy_cost: float
    created_at: str
    last_accessed: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntelligentMemoryPool:
    """Amassed reserved pooling for energy-dominant intelligence."""

    def __init__(self):
        self._lock = threading.RLock()
        self._pools: Dict[str, MemoryPool] = {}
        self._reservations: Dict[str, MemoryReservation] = {}
        self._memory_history: deque = deque(maxlen=MAX_MEMORY_HISTORY)
        self._system_total_mb = 0.0
        self._system_available_mb = 0.0
        self._energy_budget_mb = float(os.environ.get("QB_MEMORY_ENERGY_BUDGET_MB", "4096"))
        self._load_state()
        self._refresh_system_memory()

    def _load_state(self):
        if MEMORY_STATE_PATH.exists():
            try:
                with open(MEMORY_STATE_PATH, "r") as f:
                    data = json.load(f)
                for pid, p in data.get("pools", {}).items():
                    self._pools[pid] = MemoryPool(**p)
                for rid, r in data.get("reservations", {}).items():
                    self._reservations[rid] = MemoryReservation(**r)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(MEMORY_STATE_PATH, "w") as f:
                json.dump({
                    "pools": {pid: asdict(p) for pid, p in self._pools.items()},
                    "reservations": {rid: asdict(r) for rid, r in self._reservations.items()},
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _refresh_system_memory(self):
        try:
            import psutil
            mem = psutil.virtual_memory()
            self._system_total_mb = mem.total / (1024 * 1024)
            self._system_available_mb = mem.available / (1024 * 1024)
        except Exception:
            try:
                import sysctl
                hw = sysctl.get('hw.memsize')
                if hw:
                    self._system_total_mb = int(hw) / (1024 * 1024)
                else:
                    raise ValueError("hw.memsize not available")
            except Exception:
                try:
                    import subprocess
                    result = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
                    if result.returncode == 0:
                        self._system_total_mb = int(result.stdout.strip()) / (1024 * 1024)
                    else:
                        raise ValueError("sysctl hw.memsize failed")
                except Exception:
                    try:
                        import resource
                        self._system_total_mb = resource.getrlimit(resource.RLIMIT_AS)[1] / (1024 * 1024)
                    except Exception:
                        self._system_total_mb = 0.0
            try:
                import psutil
                mem = psutil.virtual_memory()
                self._system_available_mb = mem.available / (1024 * 1024)
            except Exception:
                self._system_available_mb = self._system_total_mb * 0.3

    def create_pool(self, name: str, reserved_mb: float, energy_efficiency: float = 0.8) -> MemoryPool:
        pool = MemoryPool(
            pool_id=str(uuid.uuid4()),
            name=name,
            reserved_mb=float(reserved_mb),
            allocated_mb=0.0,
            available_mb=float(reserved_mb),
            energy_efficiency=float(energy_efficiency),
            status="active",
            metadata={"created_at": datetime.utcnow().isoformat() + "Z"},
        )
        with self._lock:
            self._pools[pool.pool_id] = pool
        self._save_state()
        LOG.info("Created memory pool: %s reserved=%.1fMB", name, reserved_mb)
        return pool

    def reserve_memory(self, pool_id: str, model_id: str, reserved_mb: float, priority: int = 5) -> MemoryReservation:
        pool = self._pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        if reserved_mb > pool.available_mb:
            raise ValueError(f"Insufficient memory in pool: requested {reserved_mb}MB, available {pool.available_mb}MB")
        energy_cost = reserved_mb * (1.0 - pool.energy_efficiency)
        reservation = MemoryReservation(
            reservation_id=str(uuid.uuid4()),
            pool_id=pool_id,
            model_id=model_id,
            reserved_mb=float(reserved_mb),
            allocated_mb=float(reserved_mb),
            priority=priority,
            energy_cost=round(energy_cost, 4),
            created_at=datetime.utcnow().isoformat() + "Z",
            last_accessed=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            pool.allocated_mb += reserved_mb
            pool.available_mb -= reserved_mb
            self._reservations[reservation.reservation_id] = reservation
        self._save_state()
        LOG.info("Reserved %.1fMB for %s in pool %s", reserved_mb, model_id, pool_id)
        return reservation

    def release_reservation(self, reservation_id: str):
        reservation = self._reservations.get(reservation_id)
        if not reservation:
            return
        pool = self._pools.get(reservation.pool_id)
        if pool:
            pool.allocated_mb -= reservation.allocated_mb
            pool.available_mb += reservation.allocated_mb
        with self._lock:
            del self._reservations[reservation_id]
        self._save_state()
        LOG.info("Released reservation %s", reservation_id)

    def optimize_pools(self) -> Dict[str, Any]:
        self._refresh_system_memory()
        optimization = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "system_total_mb": round(self._system_total_mb, 2),
            "system_available_mb": round(self._system_available_mb, 2),
            "pools_optimized": 0,
            "memory_reclaimed_mb": 0.0,
            "energy_saved_mb": 0.0,
        }
        with self._lock:
            for pool in self._pools.values():
                if pool.status != "active":
                    continue
                old_allocated = pool.allocated_mb
                low_priority_reservations = [r for r in self._reservations.values() if r.pool_id == pool.pool_id and r.priority < 5]
                reclaimed = 0.0
                for reservation in low_priority_reservations:
                    reclaim_amount = reservation.allocated_mb * 0.2
                    reclaimed += reclaim_amount
                    reservation.allocated_mb -= reclaim_amount
                    pool.allocated_mb -= reclaim_amount
                    pool.available_mb += reclaim_amount
                pool.energy_efficiency = min(1.0, pool.energy_efficiency + 0.01)
                optimization["pools_optimized"] += 1
                optimization["memory_reclaimed_mb"] += reclaimed
                optimization["energy_saved_mb"] += reclaimed * (1.0 - pool.energy_efficiency)
        self._save_state()
        return optimization

    def get_pool_status(self, pool_id: str) -> Dict[str, Any]:
        pool = self._pools.get(pool_id)
        if not pool:
            return {"error": "pool_not_found"}
        reservations = [asdict(r) for r in self._reservations.values() if r.pool_id == pool_id]
        return {
            "pool": asdict(pool),
            "reservations": reservations,
            "reservation_count": len(reservations),
        }

    def get_status(self) -> Dict[str, Any]:
        self._refresh_system_memory()
        return {
            "system_total_mb": round(self._system_total_mb, 2),
            "system_available_mb": round(self._system_available_mb, 2),
            "energy_budget_mb": self._energy_budget_mb,
            "total_pools": len(self._pools),
            "total_reservations": len(self._reservations),
            "pools": [asdict(p) for p in self._pools.values()],
        }


intelligent_memory_pool = IntelligentMemoryPool()

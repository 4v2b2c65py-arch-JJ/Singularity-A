#!/usr/bin/env python3
"""
QB Protocol - VR Quest Region Management
Multi-region discovery, health checks, and failover.
"""

import os
import time
import uuid
import json
import logging
import threading
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.regions")


class RegionHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class Region:
    region_id: str
    name: str
    code: str
    endpoint: str
    health: str
    latency_ms: float
    capacity: int
    metadata: Dict[str, Any]
    last_checked: str


class RegionManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_regions.json"):
        self.state_path = state_path
        self.regions: Dict[str, Region] = {}
        self.active_region: Optional[str] = None
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for rid, r in data.get("regions", {}).items():
                        self.regions[rid] = Region(**r)
                    self.active_region = data.get("active_region")
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "regions": {rid: asdict(r) for rid, r in self.regions.items()},
                    "active_region": self.active_region,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_region(self, name: str, code: str, endpoint: str, capacity: int = 1000, metadata: Optional[Dict[str, Any]] = None) -> Region:
        region = Region(
            region_id=str(uuid.uuid4()),
            name=name,
            code=code,
            endpoint=endpoint,
            health=RegionHealth.UNKNOWN.value,
            latency_ms=0.0,
            capacity=capacity,
            metadata=metadata or {},
            last_checked=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.regions[region.region_id] = region
        self._save()
        return region

    def check_region_health(self, region_id: str) -> RegionHealth:
        with self._lock:
            region = self.regions.get(region_id)
            if not region:
                return RegionHealth.UNKNOWN

        try:
            start = time.time()
            response = requests.get(region.endpoint, timeout=5)
            latency = (time.time() - start) * 1000
            if response.status_code == 200:
                health = RegionHealth.HEALTHY if latency < 200 else RegionHealth.DEGRADED
            else:
                health = RegionHealth.UNHEALTHY
        except Exception:
            health = RegionHealth.UNHEALTHY
            latency = 0.0

        with self._lock:
            region.health = health.value
            region.latency_ms = round(latency, 2)
            region.last_checked = datetime.utcnow().isoformat() + "Z"
        self._save()
        return health

    def select_best_region(self, preferred_code: Optional[str] = None) -> Optional[Region]:
        with self._lock:
            healthy = [r for r in self.regions.values() if r.health == RegionHealth.HEALTHY.value]
            if not healthy:
                healthy = [r for r in self.regions.values() if r.health == RegionHealth.DEGRADED.value]
            if not healthy:
                return None

            if preferred_code:
                preferred = [r for r in healthy if r.code == preferred_code]
                if preferred:
                    return min(preferred, key=lambda r: r.latency_ms)

            return min(healthy, key=lambda r: r.latency_ms)

    def failover(self) -> Optional[Region]:
        with self._lock:
            old_region = self.active_region
        new_region = self.select_best_region()
        if new_region and new_region.region_id != old_region:
            with self._lock:
                self.active_region = new_region.region_id
            self._save()
            LOG.info(f"Region failover: {old_region} -> {new_region.region_id}")
            return new_region
        return None

    def get_regions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self.regions.values()]

    def get_active_region(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.active_region:
                return None
            region = self.regions.get(self.active_region)
            return asdict(region) if region else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            health_counts = {}
            for r in self.regions.values():
                health_counts[r.health] = health_counts.get(r.health, 0) + 1
            return {
                "total_regions": len(self.regions),
                "active_region": self.active_region,
                "health_distribution": health_counts,
            }


region_manager = RegionManager()

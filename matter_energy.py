#!/usr/bin/env python3
"""
QB Protocol - Matter Energy State Tracker
Tracks charged state, density weights, electron thresholds,
and determines when the model should activate for session handling.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

LOG = logging.getLogger("qb_protocol.matter_energy")

STATE_PATH = Path.home() / ".qb_protocol_matter_energy.json"
DEFAULT_THRESHOLDS = {
    "battery_critical": 0.15,
    "signal_weak": 0.4,
    "cpu_high": 0.9,
    "memory_high": 0.9,
    "uptime_low": 3600.0,
    "density_min": 0.2,
}


@dataclass
class EnergySnapshot:
    snapshot_id: str
    device_id: str
    user_id: str
    timestamp: str
    battery: float
    signal: float
    cpu: float
    memory: float
    uptime: float
    network_quality: float
    density_weight: float
    charged_state: str
    electrons_below_threshold: List[str]
    checksum: str


@dataclass
class EnergyComparison:
    comparison_id: str
    device_id: str
    previous_snapshot_id: str
    current_snapshot_id: str
    same_checks: List[str]
    different_checks: List[str]
    stability_score: float
    model_activation_recommended: bool
    reason: str
    timestamp: str


class MatterEnergyTracker:
    """Tracks matter-energy state and determines model activation."""

    def __init__(self, state_path: Path = STATE_PATH, thresholds: Dict[str, Any] = None):
        self.state_path = state_path
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.snapshots: List[EnergySnapshot] = []
        self.comparisons: List[EnergyComparison] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                for s in data.get("snapshots", []):
                    self.snapshots.append(EnergySnapshot(**s))
                for c in data.get("comparisons", []):
                    self.comparisons.append(EnergyComparison(**c))
                LOG.info("Loaded %d energy snapshots", len(self.snapshots))
            except Exception as exc:
                LOG.warning("Failed to load energy state: %s", exc)

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "snapshots": [asdict(s) for s in self.snapshots[-1000:]],
                    "comparisons": [asdict(c) for c in self.comparisons[-1000:]],
                    "thresholds": self.thresholds,
                }, f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save energy state: %s", exc)

    def _compute_checksum(self, snapshot: EnergySnapshot) -> str:
        payload = json.dumps({
            "device_id": snapshot.device_id,
            "battery": snapshot.battery,
            "signal": snapshot.signal,
            "cpu": snapshot.cpu,
            "memory": snapshot.memory,
            "uptime": snapshot.uptime,
            "network_quality": snapshot.network_quality,
            "density_weight": snapshot.density_weight,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def record_snapshot(self, device_id: str, user_id: str, metrics: Dict[str, Any]) -> EnergySnapshot:
        battery = float(metrics.get("battery", 1.0))
        signal = float(metrics.get("signal", 1.0))
        cpu = float(metrics.get("cpu", 0.0))
        memory = float(metrics.get("memory", 0.0))
        uptime = float(metrics.get("uptime", 0.0))
        network_quality = float(metrics.get("network_quality", 1.0))
        density_weight = float(metrics.get("density_weight", 1.0))
        
        electrons_below = []
        if battery < self.thresholds["battery_critical"]:
            electrons_below.append("battery")
        if signal < self.thresholds["signal_weak"]:
            electrons_below.append("signal")
        if cpu > self.thresholds["cpu_high"]:
            electrons_below.append("cpu")
        if memory > self.thresholds["memory_high"]:
            electrons_below.append("memory")
        if uptime < self.thresholds["uptime_low"]:
            electrons_below.append("uptime")
        if network_quality < self.thresholds["density_min"]:
            electrons_below.append("network_quality")
        if density_weight < self.thresholds["density_min"]:
            electrons_below.append("density_weight")
        
        if not electrons_below:
            charged_state = "stable"
        elif len(electrons_below) <= 2:
            charged_state = "degraded"
        else:
            charged_state = "critical"
        
        snapshot = EnergySnapshot(
            snapshot_id=str(uuid.uuid4()),
            device_id=device_id,
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            battery=battery,
            signal=signal,
            cpu=cpu,
            memory=memory,
            uptime=uptime,
            network_quality=network_quality,
            density_weight=density_weight,
            charged_state=charged_state,
            electrons_below_threshold=electrons_below,
            checksum="",
        )
        snapshot.checksum = self._compute_checksum(snapshot)
        
        with self._lock:
            self.snapshots.append(snapshot)
            if len(self.snapshots) > 1000:
                self.snapshots = self.snapshots[-1000:]
            self._save()
        
        LOG.info("Energy snapshot: %s state=%s electrons=%s", device_id, charged_state, electrons_below)
        return snapshot

    def compare_snapshots(self, device_id: str) -> Optional[EnergyComparison]:
        with self._lock:
            device_snapshots = [s for s in self.snapshots if s.device_id == device_id]
        
        if len(device_snapshots) < 2:
            return None
        
        prev = device_snapshots[-2]
        curr = device_snapshots[-1]
        
        same_checks = []
        different_checks = []
        
        fields = ["battery", "signal", "cpu", "memory", "uptime", "network_quality", "density_weight"]
        for field in fields:
            prev_val = getattr(prev, field)
            curr_val = getattr(curr, field)
            if abs(prev_val - curr_val) < 0.05:
                same_checks.append(field)
            else:
                different_checks.append(field)
        
        stability = len(same_checks) / max(len(fields), 1)
        
        if curr.charged_state == "critical":
            model_activation = True
            reason = "critical_energy_state"
        elif stability < 0.5 and len(curr.electrons_below_threshold) > 0:
            model_activation = True
            reason = "unstable_degraded_state"
        elif curr.charged_state == "degraded" and len(different_checks) >= 3:
            model_activation = True
            reason = "degraded_with_changing_metrics"
        else:
            model_activation = False
            reason = "stable_or_improving"
        
        comparison = EnergyComparison(
            comparison_id=str(uuid.uuid4()),
            device_id=device_id,
            previous_snapshot_id=prev.snapshot_id,
            current_snapshot_id=curr.snapshot_id,
            same_checks=same_checks,
            different_checks=different_checks,
            stability_score=round(stability, 2),
            model_activation_recommended=model_activation,
            reason=reason,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        
        with self._lock:
            self.comparisons.append(comparison)
            if len(self.comparisons) > 1000:
                self.comparisons = self.comparisons[-1000:]
            self._save()
        
        LOG.info("Energy comparison: %s stability=%.2f model=%s reason=%s", device_id, stability, model_activation, reason)
        return comparison

    def should_activate_model(self, device_id: str) -> Tuple[bool, str]:
        comparison = self.compare_snapshots(device_id)
        if not comparison:
            return False, "insufficient_data"
        return comparison.model_activation_recommended, comparison.reason

    def get_latest_snapshot(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            device_snapshots = [s for s in self.snapshots if s.device_id == device_id]
        if not device_snapshots:
            return None
        return asdict(device_snapshots[-1])

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_snapshots": len(self.snapshots),
                "total_comparisons": len(self.comparisons),
                "thresholds": self.thresholds,
                "recent_states": {
                    "stable": len([s for s in self.snapshots[-100:] if s.charged_state == "stable"]),
                    "degraded": len([s for s in self.snapshots[-100:] if s.charged_state == "degraded"]),
                    "critical": len([s for s in self.snapshots[-100:] if s.charged_state == "critical"]),
                },
            }


matter_energy = MatterEnergyTracker()

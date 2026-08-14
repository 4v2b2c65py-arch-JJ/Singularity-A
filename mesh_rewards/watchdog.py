#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Watchdog
Integrity watchdog for mesh reward transactions.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

LOG = logging.getLogger("qb_protocol.mesh_rewards.watchdog")


@dataclass
class WatchdogAlert:
    alert_id: str
    severity: str
    category: str
    message: str
    device_id: Optional[str]
    timestamp: str


class Watchdog:
    """Integrity watchdog for mesh reward network."""

    def __init__(self):
        self.alerts: List[WatchdogAlert] = []
        self._lock = threading.Lock()
        self._thresholds = {
            "max_balance_deviation": 0.5,
            "max_transfer_frequency": 10,
            "max_investigation_failures": 3,
        }

    def check_balance_integrity(self, device_id: str, expected: float, actual: float) -> bool:
        deviation = abs(expected - actual) / max(expected, 1.0)
        if deviation > self._thresholds["max_balance_deviation"]:
            self._alert("high", "balance", f"Balance deviation {deviation:.2f} for {device_id}", device_id)
            return False
        return True

    def check_transfer_frequency(self, device_id: str, recent_count: int) -> bool:
        if recent_count > self._thresholds["max_transfer_frequency"]:
            self._alert("medium", "frequency", f"High transfer frequency for {device_id}: {recent_count}", device_id)
            return False
        return True

    def check_investigation_failures(self, device_id: str, failures: int) -> bool:
        if failures > self._thresholds["max_investigation_failures"]:
            self._alert("high", "investigation", f"Excessive investigation failures for {device_id}: {failures}", device_id)
            return False
        return True

    def _alert(self, severity: str, category: str, message: str, device_id: Optional[str] = None):
        alert = WatchdogAlert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            category=category,
            message=message,
            device_id=device_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.alerts.append(alert)
        LOG.warning("Watchdog alert [%s]: %s", severity, message)

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(a) for a in self.alerts[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_alerts": len(self.alerts),
                "thresholds": self._thresholds,
            }


watchdog = Watchdog()

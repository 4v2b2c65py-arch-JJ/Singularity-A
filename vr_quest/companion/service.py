#!/usr/bin/env python3
"""
QB Protocol - VR Quest Companion Service
PC companion service states and lifecycle.
"""

import os
import time
import uuid
import json
import logging
import threading
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

LOG = logging.getLogger("qb_protocol.vr_quest.service")


class ServiceState(Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    READY = "ready"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


@dataclass
class ServiceStatus:
    state: str
    headset_connected: bool
    vrchat_detected: bool
    oscquery_connected: bool
    trackers_active: int
    last_error: str
    updated_at: str


class CompanionService:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_service.json"):
        self.state_path = state_path
        self.status = ServiceStatus(
            state=ServiceState.NOT_INSTALLED.value,
            headset_connected=False,
            vrchat_detected=False,
            oscquery_connected=False,
            trackers_active=0,
            last_error="",
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.status = ServiceStatus(**data.get("status", asdict(self.status)))
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({"status": asdict(self.status)}, f, indent=2, default=str)
        except Exception:
            pass

    def set_state(self, state: "ServiceState | str") -> ServiceStatus:
        if isinstance(state, str):
            state = ServiceState(state)
        with self._lock:
            self.status.state = state.value
            self.status.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return self.status

    def update_connection(self, headset: bool, vrchat: bool, oscquery: bool, trackers: int = 0) -> ServiceStatus:
        with self._lock:
            self.status.headset_connected = headset
            self.status.vrchat_detected = vrchat
            self.status.oscquery_connected = oscquery
            self.status.trackers_active = trackers
            self.status.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return self.status

    def record_error(self, error: str) -> ServiceStatus:
        with self._lock:
            self.status.last_error = error
            self.status.state = ServiceState.FAILED.value
            self.status.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return self.status

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self.status)

    def get_state(self) -> str:
        with self._lock:
            return self.status.state


companion_service = CompanionService()

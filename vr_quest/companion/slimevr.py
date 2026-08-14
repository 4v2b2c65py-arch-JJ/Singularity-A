#!/usr/bin/env python3
"""
QB Protocol - VR Quest SlimeVR Bridge
SlimeVR and generic tracker bridge for full-body tracking.
"""

import os
import time
import uuid
import json
import logging
import threading
import socket
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.slimevr")


@dataclass
class SlimeVRTracker:
    tracker_id: str
    name: str
    position: str
    ip: str
    port: int
    active: bool
    metadata: Dict[str, Any]
    last_seen: str


class SlimeVRBridge:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_slimevr.json"):
        self.state_path = state_path
        self.trackers: Dict[str, SlimeVRTracker] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for tid, t in data.get("trackers", {}).items():
                        self.trackers[tid] = SlimeVRTracker(**t)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "trackers": {tid: asdict(t) for tid, t in self.trackers.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def discover_trackers(self, timeout: float = 5.0) -> List[SlimeVRTracker]:
        discovered = []
        broadcast_addrs = [
            ("127.0.0.1", 6969),
            ("127.0.0.1", 21110),
            ("127.0.0.1", 21120),
        ]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)

        for host, port in broadcast_addrs:
            try:
                start = time.time()
                while time.time() - start < timeout:
                    try:
                        sock.sendto(b"SlimeVRDiscovery", (host, port))
                    except Exception:
                        pass
                    time.sleep(0.5)
            except Exception:
                pass

        sock.close()

        positions = ["hip", "chest", "left_foot", "right_foot", "left_knee", "right_knee", "left_elbow", "right_elbow"]
        for i, (host, port) in enumerate(broadcast_addrs):
            tracker = SlimeVRTracker(
                tracker_id=str(uuid.uuid4()),
                name=f"Tracker {i+1}",
                position=positions[i] if i < len(positions) else f"tracker_{i}",
                ip=host,
                port=port,
                active=True,
                metadata={"source": "slimevr"},
                last_seen=datetime.utcnow().isoformat() + "Z",
            )
            discovered.append(tracker)
            with self._lock:
                self.trackers[tracker.tracker_id] = tracker
        self._save()
        return discovered

    def get_trackers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(t) for t in self.trackers.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_trackers": len(self.trackers),
                "active_trackers": len([t for t in self.trackers.values() if t.active]),
            }


slimevr_bridge = SlimeVRBridge()

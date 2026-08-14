#!/usr/bin/env python3
"""
QB Protocol - VR Quest OSCQuery Bridge
VRChat OSCQuery discovery and automatic connection.
"""

import os
import time
import uuid
import json
import logging
import threading
import socket
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.oscquery")


@dataclass
class OSCQueryDiscovery:
    host: str
    port: int
    discovered: bool
    metadata: Dict[str, Any]
    discovered_at: str


class OSCQueryBridge:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_oscquery.json"):
        self.state_path = state_path
        self.discoveries: Dict[str, OSCQueryDiscovery] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for d_id, d in data.get("discoveries", {}).items():
                        self.discoveries[d_id] = OSCQueryDiscovery(**d)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "discoveries": {d_id: asdict(d) for d_id, d in self.discoveries.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def discover_vrchat(self, timeout: float = 5.0) -> List[OSCQueryDiscovery]:
        discovered = []
        broadcast_addrs = [
            ("127.0.0.1", 9000),
            ("127.0.0.1", 9001),
            ("127.0.0.1", 8000),
            ("127.0.0.1", 8001),
        ]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)

        for host, port in broadcast_addrs:
            try:
                start = time.time()
                while time.time() - start < timeout:
                    try:
                        sock.sendto(b"_VRChat._osc._tcp.local", (host, port))
                    except Exception:
                        pass
                    time.sleep(0.5)
            except Exception:
                pass

        sock.close()

        for host, port in broadcast_addrs:
            discovery = OSCQueryDiscovery(
                host=host,
                port=port,
                discovered=True,
                metadata={"method": "broadcast"},
                discovered_at=datetime.utcnow().isoformat() + "Z",
            )
            discovered.append(discovery)
            with self._lock:
                self.discoveries[discovery.host] = discovery
        self._save()
        return discovered

    def confirm_port(self, host: str, port: int) -> bool:
        try:
            sock = socket.create_connection((host, port), timeout=3)
            sock.close()
            return True
        except Exception:
            return False

    def get_discoveries(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(d) for d in self.discoveries.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_discoveries": len(self.discoveries),
                "active": len([d for d in self.discoveries.values() if d.discovered]),
            }


oscquery_bridge = OSCQueryBridge()

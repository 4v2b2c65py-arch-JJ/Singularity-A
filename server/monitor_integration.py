#!/usr/bin/env python3
"""
QB Protocol - Monitor Integration
Integrates fully on the monitor using the same mirror methodology.
Feeds all foreground-app ground application data to the hosted API and mirror.
"""

import time
import threading
import requests
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

try:
    from qb_protocol.stabilizers.reality_stabilizer import reality_stabilizer
    from qb_protocol.core.daemon import daemon
    from qb_protocol.dream.dream_engine import dream_engine
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stabilizers.reality_stabilizer import reality_stabilizer
    from core.daemon import daemon
    from dream.dream_engine import dream_engine


class MonitorIntegration:
    def __init__(self, api_url: str = "http://localhost:17760", mirror_url: Optional[str] = None, poll_interval: float = 1.0):
        self.api_url = api_url.rstrip("/")
        self.mirror_url = mirror_url
        self.poll_interval = poll_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = requests.post(f"{self.api_url}{path}", json=payload, timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"status": "error", "error": "unreachable"}

    def _get(self, path: str) -> Dict[str, Any]:
        try:
            resp = requests.get(f"{self.api_url}{path}", timeout=2)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {"status": "error", "error": "unreachable"}

    def _pump(self):
        while self.running:
            try:
                stabilizer = reality_stabilizer.get_status()
                dream = dream_engine.get_status()
                daemon_status = daemon.get_status()
                payload = {
                    "stabilizer": stabilizer,
                    "dream": dream,
                    "daemon": daemon_status,
                    "timestamp": time.time(),
                }
                self._post("/monitor/integrate", {"mirror_url": self.mirror_url} if self.mirror_url else {})
                for listener in self.listeners:
                    try:
                        listener(payload)
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(self.poll_interval)

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)

    def add_listener(self, listener: Callable[[Dict[str, Any]], None]):
        self.listeners.append(listener)

    def get_full_status(self) -> Dict[str, Any]:
        return {
            "api_url": self.api_url,
            "mirror_url": self.mirror_url,
            "running": self.running,
            "stabilizer": reality_stabilizer.get_status(),
            "dream": dream_engine.get_status(),
            "daemon": daemon.get_status(),
        }


monitor_integration = MonitorIntegration()

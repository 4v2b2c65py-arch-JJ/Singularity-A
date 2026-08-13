#!/usr/bin/env python3
"""
QB Protocol - Foreground App Ground Application Monitor
Monitors foreground apps and feeds stabilizers.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

try:
    from qb_protocol.stabilizers.reality_stabilizer import reality_stabilizer
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from stabilizers.reality_stabilizer import reality_stabilizer


class ForegroundAppMonitor:
    def __init__(self, poll_interval: float = 1.0):
        self.poll_interval = poll_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.current_app: Optional[Dict[str, Any]] = None
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

    def _detect_foreground(self) -> Optional[Dict[str, Any]]:
        try:
            if hasattr(platform, "macos") or platform.system() == "Darwin":
                try:
                    from AppKit import NSWorkspace
                    workspace = NSWorkspace.sharedWorkspace()
                    app = workspace.frontmostApplication()
                    if app:
                        return {
                            "app_name": app.localizedName() or "unknown",
                            "bundle_id": app.bundleIdentifier() or "unknown",
                            "pid": app.processIdentifier(),
                            "platform": "Darwin",
                        }
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def _pump(self):
        last_app = None
        while self.running:
            try:
                app = self._detect_foreground()
                if app:
                    self.current_app = app
                    reality_stabilizer.stabilize_foreground(
                        app_name=app.get("app_name", "unknown"),
                        bundle_id=app.get("bundle_id", "unknown"),
                        state="foreground",
                        temperature=0.0,
                    )
                    if last_app != app.get("bundle_id"):
                        for listener in self.listeners:
                            try:
                                listener(app)
                            except Exception:
                                pass
                        last_app = app.get("bundle_id")
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


foreground_monitor = ForegroundAppMonitor()

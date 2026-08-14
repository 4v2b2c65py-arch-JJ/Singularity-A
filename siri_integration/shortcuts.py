#!/usr/bin/env python3
"""
QB Protocol - Siri Shortcuts Manager
iOS Shortcuts integration for Siri commands.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.siri_integration.shortcuts")


@dataclass
class Shortcut:
    shortcut_id: str
    name: str
    intent: str
    action: str
    parameters: Dict[str, Any]
    siri_phrase: str
    enabled: bool
    created_at: str


class ShortcutManager:
    """Manages Siri Shortcuts for iOS."""
    
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_shortcuts.json"
        self.shortcuts: Dict[str, Shortcut] = {}
        self._lock = threading.RLock()
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("shortcuts", {}).items():
                        self.shortcuts[sid] = Shortcut(**s)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "shortcuts": {sid: asdict(s) for sid, s in self.shortcuts.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_shortcut(self, name: str, intent: str, action: str, siri_phrase: str, parameters: Dict[str, Any] = None) -> Shortcut:
        """Register a Siri Shortcut."""
        shortcut = Shortcut(
            shortcut_id=str(uuid.uuid4()),
            name=name,
            intent=intent,
            action=action,
            parameters=parameters or {},
            siri_phrase=siri_phrase,
            enabled=True,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.shortcuts[shortcut.shortcut_id] = shortcut
            self._save_state()
        return shortcut

    def get_shortcut(self, shortcut_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            shortcut = self.shortcuts.get(shortcut_id)
            return asdict(shortcut) if shortcut else None

    def get_shortcuts(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in self.shortcuts.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_shortcuts": len(self.shortcuts),
                "enabled_shortcuts": sum(1 for s in self.shortcuts.values() if s.enabled),
            }


shortcut_manager = ShortcutManager()

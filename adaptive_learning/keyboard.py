#!/usr/bin/env python3
"""
QB Protocol - Adaptive Keyboard
Learns user typing patterns, improves key predictions, adaptive layout.
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

LOG = logging.getLogger("qb_protocol.adaptive_learning.keyboard")


@dataclass
class KeyEvent:
    event_id: str
    user_id: str
    key: str
    event_type: str
    duration: float
    pressure: float
    context: Dict[str, Any]
    timestamp: str


@dataclass
class TypingPattern:
    pattern_id: str
    user_id: str
    avg_key_duration: float
    avg_pressure: float
    common_keys: List[str]
    typing_speed: float
    error_rate: float
    context: Dict[str, Any]
    created_at: str


class AdaptiveKeyboard:
    """Learns user typing patterns and improves predictions."""
    
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_keyboard.json"
        self.key_events: List[KeyEvent] = []
        self.patterns: Dict[str, TypingPattern] = {}
        self._lock = threading.RLock()
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.key_events = [KeyEvent(**e) for e in data.get("key_events", [])]
                    for pid, p in data.get("patterns", {}).items():
                        self.patterns[pid] = TypingPattern(**p)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "key_events": [asdict(e) for e in self.key_events[-10000:]],
                    "patterns": {pid: asdict(p) for pid, p in self.patterns.items()},
                }, f, indent=2, default=str)
        except Exception:
            pass

    def record_key_event(self, user_id: str, key: str, event_type: str, duration: float, pressure: float, context: Dict[str, Any] = None) -> KeyEvent:
        """Record a key event for learning."""
        event = KeyEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            key=key,
            event_type=event_type,
            duration=duration,
            pressure=pressure,
            context=context or {},
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.key_events.append(event)
            if len(self.key_events) > 100000:
                self.key_events = self.key_events[-100000:]
            self._save_state()
        return event

    def learn_pattern(self, user_id: str) -> TypingPattern:
        """Learn typing pattern for user."""
        user_events = [e for e in self.key_events if e.user_id == user_id]
        if not user_events:
            return TypingPattern(
                pattern_id=str(uuid.uuid4()),
                user_id=user_id,
                avg_key_duration=0.1,
                avg_pressure=0.5,
                common_keys=[],
                typing_speed=0.0,
                error_rate=0.0,
                context={},
                created_at=datetime.utcnow().isoformat() + "Z",
            )

        durations = [e.duration for e in user_events]
        pressures = [e.pressure for e in user_events]
        key_counts: Dict[str, int] = {}
        for e in user_events:
            key_counts[e.key] = key_counts.get(e.key, 0) + 1

        avg_duration = sum(durations) / len(durations) if durations else 0.1
        avg_pressure = sum(pressures) / len(pressures) if pressures else 0.5
        common_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        common_keys = [k for k, v in common_keys]

        typing_speed = len(user_events) / max(1, (user_events[-1].timestamp - user_events[0].timestamp)) if len(user_events) > 1 else 0.0
        error_rate = sum(1 for e in user_events if e.event_type == "error") / max(1, len(user_events))

        pattern = TypingPattern(
            pattern_id=str(uuid.uuid4()),
            user_id=user_id,
            avg_key_duration=avg_duration,
            avg_pressure=avg_pressure,
            common_keys=common_keys,
            typing_speed=typing_speed,
            error_rate=error_rate,
            context={"total_events": len(user_events)},
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        with self._lock:
            self.patterns[user_id] = pattern
            self._save_state()

        return pattern

    def predict_next_key(self, user_id: str, current_keys: List[str]) -> Optional[str]:
        """Predict next key based on learned pattern."""
        with self._lock:
            pattern = self.patterns.get(user_id)
        if not pattern or not pattern.common_keys:
            return None

        for key in pattern.common_keys:
            if key not in current_keys:
                return key
        return pattern.common_keys[0] if pattern.common_keys else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_events": len(self.key_events),
                "total_patterns": len(self.patterns),
                "users_tracked": list(self.patterns.keys()),
            }


adaptive_keyboard = AdaptiveKeyboard()

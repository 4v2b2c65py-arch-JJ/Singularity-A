#!/usr/bin/env python3
"""
QB Protocol - VR Quest Auto Reconnect
Exponential backoff reconnection logic.
"""

import os
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.auto_reconnect")


@dataclass
class ReconnectConfig:
    max_retries: int = 10
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True


@dataclass
class ReconnectAttempt:
    attempt_id: str
    attempt_number: int
    delay: float
    success: bool
    error: str
    timestamp: str


class AutoReconnect:
    def __init__(self, config: Optional[ReconnectConfig] = None, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_reconnect.json"):
        self.config = config or ReconnectConfig()
        self.state_path = state_path
        self.attempts: List[ReconnectAttempt] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.attempts = [ReconnectAttempt(**a) for a in data.get("attempts", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "attempts": [asdict(a) for a in self.attempts[-100:]]
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _calculate_delay(self, attempt: int) -> float:
        delay = self.config.initial_delay * (self.config.backoff_factor ** attempt)
        delay = min(delay, self.config.max_delay)
        if self.config.jitter:
            delay = delay * (0.5 + 0.5 * (time.time() % 1))
        return delay

    def execute(self, connect_fn: Callable[[], bool], disconnect_fn: Optional[Callable[[], None]] = None) -> Dict[str, Any]:
        last_error = ""
        for attempt in range(self.config.max_retries):
            delay = self._calculate_delay(attempt)
            time.sleep(delay)

            attempt_record = ReconnectAttempt(
                attempt_id=str(uuid.uuid4()),
                attempt_number=attempt + 1,
                delay=round(delay, 3),
                success=False,
                error="",
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

            try:
                success = connect_fn()
                attempt_record.success = success
                if success:
                    with self._lock:
                        self.attempts.append(attempt_record)
                        if len(self.attempts) > 100:
                            self.attempts = self.attempts[-100:]
                    self._save()
                    return {
                        "status": "connected",
                        "attempts": attempt + 1,
                        "total_delay": round(sum(a.delay for a in self.attempts), 3),
                    }
            except Exception as e:
                last_error = str(e)
                attempt_record.error = last_error

            with self._lock:
                self.attempts.append(attempt_record)
                if len(self.attempts) > 100:
                    self.attempts = self.attempts[-100:]
            self._save()

        if disconnect_fn:
            try:
                disconnect_fn()
            except Exception:
                pass

        return {
            "status": "failed",
            "attempts": self.config.max_retries,
            "last_error": last_error,
            "total_delay": round(sum(a.delay for a in self.attempts), 3),
        }

    def get_attempts(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(a) for a in self.attempts[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            recent = self.attempts[-10:]
            successes = len([a for a in recent if a.success])
            return {
                "total_attempts": len(self.attempts),
                "recent_success_rate": round(successes / len(recent), 2) if recent else 0,
                "config": asdict(self.config),
            }


auto_reconnect = AutoReconnect()

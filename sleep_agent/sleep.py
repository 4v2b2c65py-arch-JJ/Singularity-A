#!/usr/bin/env python3
"""
QB Protocol - Sleep Agent
Background agent that runs silently without screen flash.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.sleep_agent")


@dataclass
class SleepTask:
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int
    run_in_sleep: bool
    screen_off: bool
    created_at: str


class SleepAgent:
    """Background agent that runs silently without screen flash."""
    
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_sleep_agent.json"
        self.tasks: List[SleepTask] = []
        self.running: bool = False
        self.screen_off: bool = False
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.tasks = [SleepTask(**t) for t in data.get("tasks", [])]
                    self.screen_off = data.get("screen_off", False)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "tasks": [asdict(t) for t in self.tasks[-1000:]],
                    "screen_off": self.screen_off,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def start(self) -> Dict[str, Any]:
        """Start sleep agent."""
        with self._lock:
            if self.running:
                return {"status": "already_running"}
            self.running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            return {"status": "started", "screen_off": self.screen_off}

    def stop(self) -> Dict[str, Any]:
        """Stop sleep agent."""
        with self._lock:
            self.running = False
            self.screen_off = False
            self._save_state()
        return {"status": "stopped"}

    def _run_loop(self) -> None:
        """Main sleep agent loop."""
        while self.running:
            try:
                with self._lock:
                    pending = [t for t in self.tasks if t.run_in_sleep]
                    for task in pending:
                        self._execute_task(task)
                time.sleep(5)
            except Exception as e:
                LOG.error("Sleep agent error: %s", e)
                time.sleep(5)

    def _execute_task(self, task: SleepTask) -> None:
        """Execute task silently."""
        LOG.info("Sleep agent executing: %s", task.task_type)

    def add_task(self, task_type: str, payload: Dict[str, Any], priority: int = 5, run_in_sleep: bool = True, screen_off: bool = True) -> SleepTask:
        """Add task to sleep agent queue."""
        task = SleepTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            payload=payload,
            priority=priority,
            run_in_sleep=run_in_sleep,
            screen_off=screen_off,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.tasks.append(task)
            if len(self.tasks) > 1000:
                self.tasks = self.tasks[-1000:]
            self.screen_off = screen_off
            self._save_state()
        return task

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "screen_off": self.screen_off,
                "pending_tasks": len([t for t in self.tasks if t.run_in_sleep]),
                "total_tasks": len(self.tasks),
            }


sleep_agent = SleepAgent()

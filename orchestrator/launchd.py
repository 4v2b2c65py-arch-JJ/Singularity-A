#!/usr/bin/env python3
"""
QB Protocol - Launchd Service Manager
macOS boot persistence via launchd user agents.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
import subprocess
import plistlib
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.orchestrator.launchd")


@dataclass
class LaunchdService:
    service_id: str
    label: str
    program: str
    arguments: List[str]
    working_directory: str
    run_at_load: bool
    keep_alive: bool
    environment: Dict[str, str]
    plist_path: str
    installed: bool
    active: bool
    metadata: Dict[str, Any]
    created_at: str


class LaunchdServiceManager:
    def __init__(self):
        self.label = "com.qbprotocol.agent"
        self.services_dir = Path.home() / "Library" / "LaunchAgents"
        self.services_dir.mkdir(parents=True, exist_ok=True)
        self.plist_path = self.services_dir / f"{self.label}.plist"
        self.services: Dict[str, LaunchdService] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.plist_path.exists():
            try:
                with open(self.plist_path, "rb") as f:
                    data = plistlib.load(f)
                service = LaunchdService(
                    service_id=str(uuid.uuid4()),
                    label=self.label,
                    program=data.get("Program", ""),
                    arguments=data.get("ProgramArguments", []),
                    working_directory=data.get("WorkingDirectory", ""),
                    run_at_load=data.get("RunAtLoad", False),
                    keep_alive=data.get("KeepAlive", False),
                    environment=data.get("EnvironmentVariables", {}),
                    plist_path=str(self.plist_path),
                    installed=True,
                    active=False,
                    metadata={},
                    created_at=datetime.utcnow().isoformat() + "Z",
                )
                with self._lock:
                    self.services[service.service_id] = service
            except Exception:
                pass

    def install(self) -> Dict[str, Any]:
        with self._lock:
            if self.plist_path.exists():
                self.uninstall()

        script = Path(__file__).resolve().parent.parent / "agent.py"

        python = Path(sys.executable).resolve()
        working_dir = script.parent

        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONUNBUFFERED": "1",
        }

        plist_data = {
            "Label": self.label,
            "ProgramArguments": [str(python), str(script), "run"],
            "WorkingDirectory": str(working_dir),
            "RunAtLoad": True,
            "KeepAlive": True,
            "EnvironmentVariables": env,
            "StandardOutPath": str(Path.home() / ".qb_protocol_agent.log"),
            "StandardErrorPath": str(Path.home() / ".qb_protocol_agent_error.log"),
        }

        try:
            with open(self.plist_path, "wb") as f:
                plistlib.dump(plist_data, f)

            subprocess.run(["launchctl", "unload", str(self.plist_path)], capture_output=True)
            result = subprocess.run(["launchctl", "load", str(self.plist_path)], capture_output=True, text=True)

            if result.returncode != 0 and "already loaded" not in result.stderr.lower():
                raise RuntimeError(f"launchctl load failed: {result.stderr}")

            service = LaunchdService(
                service_id=str(uuid.uuid4()),
                label=self.label,
                program=str(python),
                arguments=[str(script), "run"],
                working_directory=str(working_dir),
                run_at_load=True,
                keep_alive=True,
                environment=env,
                plist_path=str(self.plist_path),
                installed=True,
                active=True,
                metadata={"installed_by": "orchestrator"},
                created_at=datetime.utcnow().isoformat() + "Z",
            )

            with self._lock:
                self.services[service.service_id] = service

            return {
                "status": "installed",
                "label": self.label,
                "plist_path": str(self.plist_path),
                "service_id": service.service_id,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def uninstall(self) -> Dict[str, Any]:
        try:
            subprocess.run(["launchctl", "unload", str(self.plist_path)], capture_output=True)
            if self.plist_path.exists():
                self.plist_path.unlink()

            with self._lock:
                for sid, service in list(self.services.items()):
                    if service.label == self.label:
                        service.installed = False
                        service.active = False

            return {"status": "uninstalled", "label": self.label}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["launchctl", "list", self.label],
                capture_output=True,
                text=True,
                timeout=5,
            )

            active = result.returncode == 0

            with self._lock:
                for service in self.services.values():
                    if service.label == self.label:
                        service.active = active

            return {
                "label": self.label,
                "installed": self.plist_path.exists(),
                "active": active,
                "plist_path": str(self.plist_path),
                "status": "active" if active else "inactive",
            }
        except Exception as e:
            return {
                "label": self.label,
                "installed": self.plist_path.exists(),
                "active": False,
                "error": str(e),
            }

    def start(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["launchctl", "start", self.label], capture_output=True, text=True, timeout=5)
            return {"status": "started" if result.returncode == 0 else "error", "output": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def stop(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["launchctl", "stop", self.label], capture_output=True, text=True, timeout=5)
            return {"status": "stopped" if result.returncode == 0 else "error", "output": result.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}


launchd_service = LaunchdServiceManager()

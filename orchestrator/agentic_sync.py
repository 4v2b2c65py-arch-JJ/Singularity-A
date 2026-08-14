#!/usr/bin/env python3
"""
QB Protocol - Orchestrator
Full agentic sync across macOS device.
Manages state, sync, updates, and persistence.
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
import subprocess
import plistlib
import requests
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

LOG = logging.getLogger("qb_protocol.orchestrator")


class SyncStatus(Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    UPDATING = "updating"
    ERROR = "error"
    PERSISTED = "persisted"


class DeviceState(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    SYNCING = "syncing"
    UPDATING = "updating"
    REBOOTING = "rebooting"


@dataclass
class AgenticSync:
    sync_id: str
    device_id: str
    status: str
    state: str
    last_sync: str
    last_update: str
    boot_count: int
    version: str
    changes: List[str]
    metadata: Dict[str, Any]
    timestamp: str


class Orchestrator:
    def __init__(self, state_path: Optional[Path] = None, repo_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_orchestrator.json"
        self.repo_path = repo_path or Path(__file__).resolve().parent.parent.parent.parent
        self.device_id = self._get_device_id()
        self.version = self._get_version()
        self.boot_count = 0
        self.status = SyncStatus.IDLE.value
        self.state = DeviceState.ONLINE.value
        self.changes: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.last_sync: Optional[str] = None
        self.last_update: Optional[str] = None
        self._lock = threading.RLock()
        self._load()
        self._boot_count = self.boot_count
        self._boot()

    def _get_device_id(self) -> str:
        try:
            import uuid
            node = uuid.getnode()
            if node and node != 0:
                return f"mac-{node:012x}"
        except Exception:
            pass
        return f"mac-{uuid.uuid4().hex[:12]}"

    def _get_version(self) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def _boot(self) -> None:
        with self._lock:
            self.boot_count += 1
            self.state = DeviceState.ONLINE.value
            self.status = SyncStatus.SYNCING.value
            self.changes.append(f"boot_{self.boot_count}")
            self._save()
            LOG.info(f"Orchestrator boot #{self.boot_count} on {self.device_id}")

    def _load(self) -> None:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.boot_count = data.get("boot_count", 0)
                    self.last_sync = data.get("last_sync")
                    self.last_update = data.get("last_update")
                    self.version = data.get("version", self.version)
                    self.changes = data.get("changes", [])
                    self.metadata = data.get("metadata", {})
            except Exception:
                pass

    def _save(self) -> None:
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "device_id": self.device_id,
                    "version": self.version,
                    "boot_count": self.boot_count,
                    "last_sync": self.last_sync,
                    "last_update": self.last_update,
                    "status": self.status,
                    "state": self.state,
                    "changes": self.changes[-100:],
                    "metadata": self.metadata,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }, f, indent=2, default=str)
        except Exception:
            pass

    def sync(self, direction: str = "bidirectional") -> Dict[str, Any]:
        with self._lock:
            self.status = SyncStatus.SYNCING.value
            self.state = DeviceState.SYNCING.value
            self._save()

        try:
            start = time.time()
            changes_count = 0

            if direction in ("bidirectional", "upload"):
                changes_count += self._upload_changes()

            if direction in ("bidirectional", "download"):
                changes_count += self._download_changes()

            latency = (time.time() - start) * 1000
            self.last_sync = datetime.utcnow().isoformat() + "Z"
            self.status = SyncStatus.PERSISTED.value
            self.state = DeviceState.ONLINE.value

            result = {
                "sync_id": str(uuid.uuid4()),
                "status": "ok",
                "direction": direction,
                "changes_count": changes_count,
                "latency_ms": latency,
                "device_id": self.device_id,
                "version": self.version,
                "last_sync": self.last_sync,
            }

            with self._lock:
                self.changes.append(f"sync_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
                self._save()

            return result

        except Exception as e:
            self.status = SyncStatus.ERROR.value
            self.state = DeviceState.OFFLINE.value
            self._save()
            return {
                "sync_id": str(uuid.uuid4()),
                "status": "error",
                "error": str(e),
                "device_id": self.device_id,
            }

    def _upload_changes(self) -> int:
        try:
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                return 0

            subprocess.run(
                ["git", "-C", str(self.repo_path), "add", "-A"],
                capture_output=True,
                timeout=10,
            )

            status = subprocess.run(
                ["git", "-C", str(self.repo_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if status.stdout.strip():
                subprocess.run(
                    ["git", "-C", str(self.repo_path), "commit", "-m", f"orchestrator sync {datetime.utcnow().isoformat()}"],
                    capture_output=True,
                    timeout=10,
                )

                subprocess.run(
                    ["git", "-C", str(self.repo_path), "push", "origin", "main"],
                    capture_output=True,
                    timeout=30,
                )

                return len(status.stdout.strip().splitlines())
        except Exception as e:
            LOG.warning("Upload changes failed: %s", e)
        return 0

    def _download_changes(self) -> int:
        try:
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                return 0

            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "pull", "origin", "main"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                count = result.stdout.count("\n")
                return max(0, count - 2)
        except Exception as e:
            LOG.warning("Download changes failed: %s", e)
        return 0

    def update(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            self.status = SyncStatus.UPDATING.value
            self.state = DeviceState.UPDATING.value
            self._save()

        try:
            start = time.time()

            if target_version:
                result = subprocess.run(
                    ["git", "-C", str(self.repo_path), "fetch", "origin"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Git fetch failed: {result.stderr}")

                result = subprocess.run(
                    ["git", "-C", str(self.repo_path), "checkout", target_version],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Git checkout failed: {result.stderr}")
            else:
                result = subprocess.run(
                    ["git", "-C", str(self.repo_path), "pull", "origin", "main"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Git pull failed: {result.stderr}")

            self.version = self._get_version()
            self.last_update = datetime.utcnow().isoformat() + "Z"
            latency = (time.time() - start) * 1000

            self.status = SyncStatus.PERSISTED.value
            self.state = DeviceState.ONLINE.value

            result = {
                "update_id": str(uuid.uuid4()),
                "status": "ok",
                "version": self.version,
                "target_version": target_version or "main",
                "latency_ms": latency,
                "device_id": self.device_id,
            }

            with self._lock:
                self.changes.append(f"update_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
                self._save()

            return result

        except Exception as e:
            self.status = SyncStatus.ERROR.value
            self.state = DeviceState.OFFLINE.value
            self._save()
            return {
                "update_id": str(uuid.uuid4()),
                "status": "error",
                "error": str(e),
                "device_id": self.device_id,
            }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "device_id": self.device_id,
                "version": self.version,
                "status": self.status,
                "state": self.state,
                "boot_count": self.boot_count,
                "last_sync": self.last_sync,
                "last_update": self.last_update,
                "changes_count": len(self.changes),
                "uptime_seconds": time.time() - getattr(self, '_boot_time', time.time()),
                "metadata": self.metadata,
            }

    def get_changes(self, limit: int = 100) -> List[str]:
        with self._lock:
            return self.changes[-limit:]

    def reboot_device(self, delay: int = 0) -> Dict[str, Any]:
        with self._lock:
            self.state = DeviceState.REBOOTING.value
            self.changes.append(f"reboot_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
            self._save()

        def _do_reboot():
            if delay > 0:
                time.sleep(delay)
            try:
                subprocess.run(["sudo", "shutdown", "-r", "+1"], timeout=5)
            except Exception as e:
                LOG.error("Reboot failed: %s", e)

        thread = threading.Thread(target=_do_reboot, daemon=True)
        thread.start()

        return {
            "reboot_id": str(uuid.uuid4()),
            "status": "scheduled",
            "delay_seconds": delay,
            "device_id": self.device_id,
        }

    def install_service(self) -> Dict[str, Any]:
        try:
            from orchestrator.launchd import launchd_service
            result = launchd_service.install()
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def uninstall_service(self) -> Dict[str, Any]:
        try:
            from orchestrator.launchd import launchd_service
            result = launchd_service.uninstall()
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_service_status(self) -> Dict[str, Any]:
        try:
            from orchestrator.launchd import launchd_service
            return launchd_service.get_status()
        except Exception as e:
            return {"status": "error", "error": str(e)}


orchestrator = Orchestrator()

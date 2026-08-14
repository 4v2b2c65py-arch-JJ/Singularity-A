#!/usr/bin/env python3
"""
QB Protocol - Auto Updater
Progressive auto updates and synchronization.
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
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.orchestrator.auto_update")


@dataclass
class UpdateManifest:
    version: str
    commit_hash: str
    timestamp: str
    files_changed: int
    download_url: str
    checksum: str
    changelog: str


class AutoUpdater:
    def __init__(self, repo_path: Optional[Path] = None, update_url: Optional[str] = None):
        self.repo_path = repo_path or Path(__file__).resolve().parent.parent.parent.parent
        self.update_url = update_url or os.environ.get("QB_UPDATE_URL", "")
        self.current_version = self._get_current_version()
        self.last_check: Optional[str] = None
        self.last_update: Optional[str] = None
        self.update_history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._load_history()

    def _get_current_version(self) -> str:
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

    def _load_history(self):
        history_path = self.repo_path / "qb_protocol_updates.json"
        if history_path.exists():
            try:
                with open(history_path, "r") as f:
                    self.update_history = json.load(f).get("updates", [])
            except Exception:
                pass

    def _save_history(self):
        try:
            history_path = self.repo_path / "qb_protocol_updates.json"
            with open(history_path, "w") as f:
                json.dump({"updates": self.update_history[-100:]}, f, indent=2, default=str)
        except Exception:
            pass

    def check_for_updates(self) -> Dict[str, Any]:
        self.last_check = datetime.utcnow().isoformat() + "Z"

        if not self.update_url:
            return {
                "update_available": False,
                "current_version": self.current_version,
                "last_check": self.last_check,
                "reason": "no_update_url_configured",
            }

        try:
            response = requests.get(self.update_url, timeout=10)
            if response.status_code != 200:
                return {
                    "update_available": False,
                    "current_version": self.current_version,
                    "last_check": self.last_check,
                    "reason": f"update_server_error_{response.status_code}",
                }

            manifest_data = response.json()
            manifest = UpdateManifest(**manifest_data)

            has_update = manifest.commit_hash != self._get_full_hash(self.current_version)

            return {
                "update_available": has_update,
                "current_version": self.current_version,
                "latest_version": manifest.version,
                "latest_commit": manifest.commit_hash,
                "timestamp": manifest.timestamp,
                "files_changed": manifest.files_changed,
                "changelog": manifest.changelog,
                "last_check": self.last_check,
            }

        except Exception as e:
            return {
                "update_available": False,
                "current_version": self.current_version,
                "last_check": self.last_check,
                "error": str(e),
            }

    def apply_update(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        start = time.time()
        update_id = str(uuid.uuid4())

        with self._lock:
            self.last_update = datetime.utcnow().isoformat() + "Z"

        try:
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                return {"status": "error", "error": "not_a_git_repository"}

            subprocess.run(["git", "-C", str(self.repo_path), "fetch", "origin"], capture_output=True, timeout=30)

            if target_version:
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

            new_version = self._get_current_version()
            latency = (time.time() - start) * 1000

            record = {
                "update_id": update_id,
                "status": "ok",
                "from_version": self.current_version,
                "to_version": new_version,
                "target_version": target_version or "main",
                "latency_ms": latency,
                "timestamp": self.last_update,
            }

            with self._lock:
                self.update_history.append(record)
                self.current_version = new_version
                self._save_history()

            return record

        except Exception as e:
            return {
                "update_id": update_id,
                "status": "error",
                "error": str(e),
                "timestamp": self.last_update,
            }

    def _get_full_hash(self, short_hash: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", short_hash],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return short_hash

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_version": self.current_version,
                "last_check": self.last_check,
                "last_update": self.last_update,
                "update_history_count": len(self.update_history),
                "update_url": self.update_url,
            }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return self.update_history[-limit:]


auto_updater = AutoUpdater()

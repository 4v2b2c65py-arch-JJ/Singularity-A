#!/usr/bin/env python3
"""
QB Protocol - GitHub Manager
Automatic git and GitHub management across the multiverse.
Handles commits, pushes, addons, and global GitHub integration.
"""

import os
import time
import uuid
import json
import logging
import threading
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.github_manager")


class OperationStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    CONFLICT = "conflict"


@dataclass
class GitOperation:
    operation_id: str
    operation_type: str
    status: str
    message: str
    timestamp: str
    details: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class AddonInfo:
    addon_id: str
    name: str
    description: str
    source: str
    version: str
    installed: bool
    enabled: bool
    dependencies: List[str]
    metadata: Dict[str, Any]


@dataclass
class SessionInfo:
    session_id: str
    branch: str
    commit_hash: str
    start_time: str
    end_time: Optional[str]
    active: bool
    participants: List[str]
    data_transferred: int
    metadata: Dict[str, Any]


class GitHubManager:
    def __init__(self, repo_path: Path = Path("."), github_token: Optional[str] = None):
        self.repo_path = Path(repo_path).resolve()
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.operations: List[GitOperation] = []
        self.addons: Dict[str, AddonInfo] = {}
        self.sessions: Dict[str, SessionInfo] = {}
        self._lock = threading.RLock()
        self._load_state()
        self._detect_addons()
        self._init_git_config()

    def _load_state(self):
        state_file = self.repo_path / "qb_protocol_github_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r") as f:
                    data = json.load(f)
                    self.addons = {aid: AddonInfo(**a) for aid, a in data.get("addons", {}).items()}
                    self.sessions = {sid: SessionInfo(**s) for sid, s in data.get("sessions", {}).items()}
            except Exception:
                pass

    def _save_state(self):
        state_file = self.repo_path / "qb_protocol_github_state.json"
        try:
            with open(state_file, "w") as f:
                json.dump({
                    "addons": {aid: asdict(a) for aid, a in self.addons.items()},
                    "sessions": {sid: asdict(s) for sid, s in self.sessions.items()},
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _init_git_config(self):
        try:
            if not self._git(["config", "user.name"]):
                self._git(["config", "user.name", "QB Protocol"])
            if not self._git(["config", "user.email"]):
                self._git(["config", "user.email", "qb-protocol@multiverse.local"])
        except Exception:
            pass

    def _git(self, args: List[str], cwd: Optional[Path] = None) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            LOG.debug(f"git {' '.join(args)}: {result.stderr.strip()}")
            return None
        except Exception as e:
            LOG.debug(f"git error: {e}")
            return None

    def _record_operation(self, op_type: str, status: OperationStatus, message: str, details: Optional[Dict[str, Any]] = None) -> GitOperation:
        op = GitOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=op_type,
            status=status.value,
            message=message,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details=details or {},
        )
        with self._lock:
            self.operations.append(op)
            if len(self.operations) > 1000:
                self.operations = self.operations[-1000:]
        return op

    def _detect_addons(self):
        addon_dirs = ["agent", "ai", "api", "chat", "core", "deploy", "dream", "engine", "evolution", "frontend", "gateway", "models", "oracle", "package", "platform_pkg", "rate", "sdk", "server", "stabilizers", "utils", "vemex"]
        for addon_name in addon_dirs:
            addon_path = self.repo_path / addon_name
            if addon_path.exists() and addon_path.is_dir():
                if addon_name not in self.addons:
                    self.addons[addon_name] = AddonInfo(
                        addon_id=str(uuid.uuid4()),
                        name=addon_name,
                        description=f"Auto-detected addon: {addon_name}",
                        source="local",
                        version="1.0.0",
                        installed=True,
                        enabled=True,
                        dependencies=[],
                        metadata={"path": str(addon_path)},
                    )
        self._save_state()

    def stage_changes(self, paths: Optional[List[str]] = None) -> GitOperation:
        if paths is None:
            paths = ["."]
        result = self._git(["add"] + paths)
        if result is not None:
            return self._record_operation("stage", OperationStatus.SUCCESS, f"Staged {len(paths)} paths", {"paths": paths})
        return self._record_operation("stage", OperationStatus.FAILED, "Failed to stage changes")

    def commit(self, message: str, auto_stage: bool = True) -> GitOperation:
        if auto_stage:
            self.stage_changes()
        result = self._git(["commit", "-m", message])
        if result:
            return self._record_operation("commit", OperationStatus.SUCCESS, message, {"output": result})
        return self._record_operation("commit", OperationStatus.FAILED, "Failed to commit")

    def push(self, remote: str = "origin", branch: str = "main") -> GitOperation:
        result = self._git(["push", remote, branch])
        if result:
            return self._record_operation("push", OperationStatus.SUCCESS, f"Pushed to {remote}/{branch}", {"remote": remote, "branch": branch})
        return self._record_operation("push", OperationStatus.FAILED, f"Failed to push to {remote}/{branch}")

    def auto_commit_push(self, message_template: str = "QB Protocol: auto-sync {timestamp}") -> Dict[str, Any]:
        status = self._git(["status", "--porcelain"])
        if not status:
            return {"status": OperationStatus.SUCCESS.value, "message": "No changes to commit"}
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        message = message_template.format(timestamp=timestamp)
        commit_op = self.commit(message)
        if commit_op.status == OperationStatus.SUCCESS.value:
            push_op = self.push()
            return {
                "status": push_op.status,
                "message": push_op.message,
                "commit": commit_op.message,
                "push": push_op.details,
            }
        return {"status": commit_op.status, "message": commit_op.message}

    def create_branch(self, branch_name: str, checkout: bool = True) -> GitOperation:
        result = self._git(["branch", branch_name])
        if result:
            if checkout:
                self._git(["checkout", branch_name])
            return self._record_operation("create_branch", OperationStatus.SUCCESS, f"Created branch {branch_name}", {"branch": branch_name})
        return self._record_operation("create_branch", OperationStatus.FAILED, f"Failed to create branch {branch_name}")

    def switch_branch(self, branch_name: str) -> GitOperation:
        result = self._git(["checkout", branch_name])
        if result:
            return self._record_operation("switch_branch", OperationStatus.SUCCESS, f"Switched to {branch_name}", {"branch": branch_name})
        return self._record_operation("switch_branch", OperationStatus.FAILED, f"Failed to switch to {branch_name}")

    def get_status(self) -> Dict[str, Any]:
        branch = self._git(["branch", "--show-current"]) or "unknown"
        commit_hash = self._git(["rev-parse", "HEAD"]) or "unknown"
        status = self._git(["status", "--porcelain"]) or ""
        changes = [line.strip() for line in status.split("\n") if line.strip()]
        return {
            "branch": branch,
            "commit_hash": commit_hash[:12] if commit_hash != "unknown" else commit_hash,
            "changes": changes[:50],
            "change_count": len(changes),
            "addons_installed": len([a for a in self.addons.values() if a.installed]),
            "addons_enabled": len([a for a in self.addons.values() if a.enabled]),
        }

    def get_addons(self) -> List[Dict[str, Any]]:
        return [asdict(a) for a in self.addons.values()]

    def enable_addon(self, addon_id: str) -> Dict[str, Any]:
        with self._lock:
            addon = self.addons.get(addon_id)
            if not addon:
                return {"status": OperationStatus.FAILED.value, "message": f"Addon {addon_id} not found"}
            addon.enabled = True
            self._save_state()
            return {"status": OperationStatus.SUCCESS.value, "message": f"Addon {addon.name} enabled", "addon": asdict(addon)}

    def disable_addon(self, addon_id: str) -> Dict[str, Any]:
        with self._lock:
            addon = self.addons.get(addon_id)
            if not addon:
                return {"status": OperationStatus.FAILED.value, "message": f"Addon {addon_id} not found"}
            addon.enabled = False
            self._save_state()
            return {"status": OperationStatus.SUCCESS.value, "message": f"Addon {addon.name} disabled", "addon": asdict(addon)}

    def install_addon(self, addon_path: Path) -> Dict[str, Any]:
        target = self.repo_path / addon_path.name
        try:
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(addon_path, target)
            self._detect_addons()
            return {"status": OperationStatus.SUCCESS.value, "message": f"Addon {addon_path.name} installed"}
        except Exception as e:
            return {"status": OperationStatus.FAILED.value, "message": str(e)}

    def start_session(self, branch: Optional[str] = None) -> SessionInfo:
        if branch is None:
            branch = self._git(["branch", "--show-current"]) or "main"
        commit_hash = self._git(["rev-parse", "HEAD"]) or "unknown"
        session = SessionInfo(
            session_id=str(uuid.uuid4()),
            branch=branch,
            commit_hash=commit_hash[:12] if commit_hash != "unknown" else commit_hash,
            start_time=datetime.utcnow().isoformat() + "Z",
            end_time=None,
            active=True,
            participants=[],
            data_transferred=0,
            metadata={},
        )
        with self._lock:
            self.sessions[session.session_id] = session
        self._save_state()
        return session

    def end_session(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": OperationStatus.FAILED.value, "message": f"Session {session_id} not found"}
            session.active = False
            session.end_time = datetime.utcnow().isoformat() + "Z"
            self._save_state()
            return {"status": OperationStatus.SUCCESS.value, "message": f"Session {session_id} ended", "session": asdict(session)}

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in self.sessions.values() if s.active]

    def share_session(self, session_id: str, participant_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": OperationStatus.FAILED.value, "message": f"Session {session_id} not found"}
            if participant_id not in session.participants:
                session.participants.append(participant_id)
            self._save_state()
            return {"status": OperationStatus.SUCCESS.value, "message": f"Shared session {session_id} with {participant_id}", "participants": session.participants}

    def get_status(self) -> Dict[str, Any]:
        git_status = self.get_status()
        return {
            "git": git_status,
            "operations": len(self.operations),
            "addons": len(self.addons),
            "sessions": len(self.sessions),
            "active_sessions": len([s for s in self.sessions.values() if s.active]),
        }


github_manager = GitHubManager()

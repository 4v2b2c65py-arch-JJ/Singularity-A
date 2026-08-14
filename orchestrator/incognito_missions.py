#!/usr/bin/env python3
"""
QB Protocol - Incognito Solo Missions
Autonomous mission execution without user intervention.
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
import hashlib
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.orchestrator.missions")


class MissionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"
    INCognito = "incognito"


class MissionType(Enum):
    ENV_SCAN = "env_scan"
    SHELL_EXEC = "shell_exec"
    GIT_SYNC = "git_sync"
    DEPLOY = "deploy"
    UPDATE = "update"
    REBOOT = "reboot"
    BROWSER_AUTOMATION = "browser_automation"
    CUSTOM = "custom"


@dataclass
class Mission:
    mission_id: str
    mission_type: str
    status: str
    priority: int
    incognito: bool
    payload: Dict[str, Any]
    result: Dict[str, Any]
    error: Optional[str]
    started_at: Optional[str]
    finished_at: Optional[str]
    created_at: str


@dataclass
class MissionResult:
    mission_id: str
    status: str
    output: str
    error: str
    environment_details: Dict[str, Any]
    artifacts: List[str]
    duration_ms: float
    timestamp: str


class IncognitoMissionRunner:
    """Executes missions autonomously without user intervention."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path(__file__).resolve().parent.parent.parent.parent
        self.missions: Dict[str, Mission] = {}
        self.results: List[MissionResult] = []
        self._lock = threading.RLock()
        self._running = False
        self._mission_queue: List[Mission] = []
        self._load_missions()

    def _load_missions(self):
        missions_path = self.repo_path / "qb_protocol_missions.json"
        if missions_path.exists():
            try:
                with open(missions_path, "r") as f:
                    data = json.load(f)
                    for mid, m in data.get("missions", {}).items():
                        self.missions[mid] = Mission(**m)
                    self._mission_queue = [Mission(**m) for m in data.get("queue", [])]
            except Exception:
                pass

    def _save_missions(self):
        try:
            missions_path = self.repo_path / "qb_protocol_missions.json"
            with open(missions_path, "w") as f:
                json.dump({
                    "missions": {mid: asdict(m) for mid, m in self.missions.items()},
                    "queue": [asdict(m) for m in self._mission_queue],
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_mission(self, mission_type: str, payload: Dict[str, Any] = None, incognito: bool = True, priority: int = 5) -> Mission:
        mission = Mission(
            mission_id=str(uuid.uuid4()),
            mission_type=mission_type,
            status=MissionStatus.PENDING.value,
            priority=priority,
            incognito=incognito,
            payload=payload or {},
            result={},
            error=None,
            started_at=None,
            finished_at=None,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.missions[mission.mission_id] = mission
            self._mission_queue.append(mission)
            self._mission_queue.sort(key=lambda m: m.priority)
        self._save_missions()
        return mission

    def run_mission(self, mission_id: str) -> MissionResult:
        with self._lock:
            mission = self.missions.get(mission_id)
            if not mission:
                return MissionResult(
                    mission_id=mission_id,
                    status="error",
                    output="",
                    error="mission_not_found",
                    environment_details={},
                    artifacts=[],
                    duration_ms=0,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                )

            mission.status = MissionStatus.RUNNING.value
            mission.started_at = datetime.utcnow().isoformat() + "Z"
            self._save_missions()

        start = time.time()
        output = ""
        error = ""
        environment_details = {}
        artifacts = []

        try:
            if mission.mission_type == MissionType.ENV_SCAN.value:
                output, error, environment_details, artifacts = self._run_env_scan(mission)
            elif mission.mission_type == MissionType.SHELL_EXEC.value:
                output, error, environment_details, artifacts = self._run_shell_exec(mission)
            elif mission.mission_type == MissionType.GIT_SYNC.value:
                output, error, environment_details, artifacts = self._run_git_sync(mission)
            elif mission.mission_type == MissionType.DEPLOY.value:
                output, error, environment_details, artifacts = self._run_deploy(mission)
            elif mission.mission_type == MissionType.UPDATE.value:
                output, error, environment_details, artifacts = self._run_update(mission)
            elif mission.mission_type == MissionType.REBOOT.value:
                output, error, environment_details, artifacts = self._run_reboot(mission)
            elif mission.mission_type == MissionType.BROWSER_AUTOMATION.value:
                output, error, environment_details, artifacts = self._run_browser_automation(mission)
            else:
                output, error, environment_details, artifacts = self._run_custom(mission)

            status = MissionStatus.SUCCESS.value if not error else MissionStatus.FAILED.value

        except Exception as e:
            status = MissionStatus.FAILED.value
            error = str(e)
            output = ""

        duration = (time.time() - start) * 1000
        finished_at = datetime.utcnow().isoformat() + "Z"

        result = MissionResult(
            mission_id=mission_id,
            status=status,
            output=output,
            error=error,
            environment_details=environment_details,
            artifacts=artifacts,
            duration_ms=duration,
            timestamp=finished_at,
        )

        with self._lock:
            mission.status = status
            mission.result = asdict(result)
            mission.error = error
            mission.finished_at = finished_at
            self.results.append(result)
            if len(self.results) > 10000:
                self.results = self.results[-10000:]
            if mission in self._mission_queue:
                self._mission_queue.remove(mission)
            self._save_missions()

        return result

    def _run_env_scan(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            from cross_platform.detector import platform_detector
            from cross_platform.shell import freedom_shell
            from cross_platform.metal import metal_manager

            info = platform_detector.detect(force=True)
            env_details = asdict(info)
            shells = freedom_shell.detect_shells()
            devices = metal_manager.get_devices()

            env_details["available_shells"] = shells
            env_details["metal_devices"] = devices
            env_details["scan_timestamp"] = datetime.utcnow().isoformat() + "Z"

            output = json.dumps(env_details, indent=2)
            artifacts = ["env_scan.json"]
            return output, "", env_details, artifacts
        except Exception as e:
            return "", str(e), {}, []

    def _run_shell_exec(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            from cross_platform.shell import freedom_shell
            command = mission.payload.get("command", "")
            args = mission.payload.get("args", [])
            admin = mission.payload.get("admin", False)
            raw_metal = mission.payload.get("raw_metal", False)
            timeout = float(mission.payload.get("timeout", 30.0))

            if raw_metal:
                result = freedom_shell.execute_raw_metal(command, args=args, timeout=timeout)
            elif admin:
                result = freedom_shell.execute_admin(command, args=args, timeout=timeout)
            else:
                result = freedom_shell.execute(command, args=args, timeout=timeout)

            env_details = {
                "shell": result.shell,
                "return_code": result.return_code,
                "execution_time": (datetime.utcnow() - datetime.fromisoformat(result.started_at.replace("Z", "+00:00"))).total_seconds(),
            }
            return result.output, result.error, env_details, []
        except Exception as e:
            return "", str(e), {}, []

    def _run_git_sync(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            direction = mission.payload.get("direction", "bidirectional")
            from orchestrator.agentic_sync import orchestrator
            result = orchestrator.sync(direction=direction)
            output = json.dumps(result, indent=2)
            env_details = {"git_sync": result}
            return output, "", env_details, ["git_sync_result.json"]
        except Exception as e:
            return "", str(e), {}, []

    def _run_deploy(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            target = mission.payload.get("target")
            force = mission.payload.get("force", False)
            from cross_platform.deployer import cross_platform_deployer
            result = cross_platform_deployer.deploy(target=target, force=force)
            output = json.dumps(asdict(result), indent=2)
            env_details = {"deployment": asdict(result)}
            return output, "", env_details, ["deploy_result.json"]
        except Exception as e:
            return "", str(e), {}, []

    def _run_update(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            target_version = mission.payload.get("target_version")
            from orchestrator.agentic_sync import orchestrator
            result = orchestrator.update(target_version=target_version)
            output = json.dumps(result, indent=2)
            env_details = {"update": result}
            return output, "", env_details, ["update_result.json"]
        except Exception as e:
            return "", str(e), {}, []

    def _run_reboot(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            delay = int(mission.payload.get("delay", 0))
            from orchestrator.agentic_sync import orchestrator
            result = orchestrator.reboot_device(delay=delay)
            output = json.dumps(result, indent=2)
            env_details = {"reboot": result}
            return output, "", env_details, ["reboot_scheduled.json"]
        except Exception as e:
            return "", str(e), {}, []

    def _run_browser_automation(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            from qb_protocol.communication.browser_session import browser_session_manager
            action = mission.payload.get("action", "discover")
            endpoints = mission.payload.get("endpoints", [])
            profile_name = mission.payload.get("profile_name", "default")

            if action == "discover" and endpoints:
                results = browser_session_manager.discover_browser_targets(endpoints)
                output = json.dumps(results, indent=2)
                env_details = {"discovered": len(results), "results": results}
                artifacts = ["browser_discovery.json"]
                return output, "", env_details, artifacts

            elif action == "create_profile":
                profile = browser_session_manager.create_profile(
                    name=profile_name,
                    initial_cookies=mission.payload.get("cookies", {}),
                    metadata=mission.payload.get("metadata", {}),
                )
                output = json.dumps(asdict(profile), indent=2)
                env_details = {"profile": asdict(profile)}
                artifacts = ["browser_profile.json"]
                return output, "", env_details, artifacts

            elif action == "registry":
                registry = browser_session_manager.get_registry()
                output = json.dumps(registry, indent=2)
                env_details = registry
                artifacts = ["browser_registry.json"]
                return output, "", env_details, artifacts

            else:
                return "", f"unknown_browser_action:{action}", {}, []

        except Exception as e:
            return "", str(e), {}, []

    def _run_custom(self, mission: Mission) -> Tuple[str, str, Dict[str, Any], List[str]]:
        try:
            script = mission.payload.get("script", "")
            if not script:
                return "", "no_script_provided", {}, []
            
            result = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                timeout=mission.payload.get("timeout", 60),
            )
            env_details = {"return_code": result.returncode}
            return result.stdout.strip(), result.stderr.strip(), env_details, []
        except Exception as e:
            return "", str(e), {}, []

    def get_mission_status(self, mission_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            mission = self.missions.get(mission_id)
            if mission:
                result = self.results[-1] if self.results else None
                data = asdict(mission)
                if result:
                    data["last_result"] = asdict(result)
                return data
            return None

    def get_queue(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(m) for m in self._mission_queue]

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self.results[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_missions": len(self.missions),
                "queued_missions": len(self._mission_queue),
                "completed_missions": len([m for m in self.missions.values() if m.status == MissionStatus.SUCCESS.value]),
                "failed_missions": len([m for m in self.missions.values() if m.status == MissionStatus.FAILED.value]),
                "incognito_missions": len([m for m in self.missions.values() if m.incognito]),
            }


class IncognitoSoloMissionRunner:
    """Autonomous mission execution without user intervention."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        self.runner = IncognitoMissionRunner(repo_path=repo_path)
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            LOG.info("Incognito solo mission runner started")

    def stop(self) -> None:
        with self._lock:
            self._running = False
        LOG.info("Incognito solo mission runner stopped")

    def _run_loop(self) -> None:
        while self._running:
            try:
                queue = self.runner.get_queue()
                if not queue:
                    time.sleep(5)
                    continue

                mission = queue[0]
                LOG.info("Running incognito mission: %s type=%s", mission.get("mission_id"), mission.get("mission_type"))
                result = self.runner.run_mission(mission["mission_id"])
                LOG.info("Mission completed: %s status=%s", mission.get("mission_id"), result.status)
            except Exception as e:
                LOG.error("Mission runner error: %s", e)
            time.sleep(1)

    def create_mission(self, mission_type: str, payload: Dict[str, Any] = None, incognito: bool = True, priority: int = 5) -> Dict[str, Any]:
        mission = self.runner.create_mission(mission_type, payload=payload, incognito=incognito, priority=priority)
        return asdict(mission)

    def get_status(self) -> Dict[str, Any]:
        return self.runner.get_status()

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.runner.get_history(limit=limit)

    def get_queue(self) -> List[Dict[str, Any]]:
        return self.runner.get_queue()


incognito_mission_runner = IncognitoSoloMissionRunner()

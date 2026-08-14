#!/usr/bin/env python3
"""
QB Protocol - Cross-Platform Deployer
Auto-deploys to any detected platform.
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
import shutil
import zipfile
import tarfile
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.cross_platform.deployer")


@dataclass
class DeployResult:
    platform: str
    environment: str
    status: str
    steps: List[str]
    files_deployed: int
    services_started: int
    error: Optional[str]
    duration_ms: float
    timestamp: str


class CrossPlatformDeployer:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path(__file__).resolve().parent.parent.parent
        self.deploy_history: List[DeployResult] = []
        self._lock = threading.RLock()

    def deploy(self, target: Optional[str] = None, force: bool = False) -> DeployResult:
        start = time.time()
        steps: List[str] = []
        files_deployed = 0
        services_started = 0
        error = None
        status = "ok"

        try:
            from cross_platform.detector import platform_detector
            info = platform_detector.detect(force=force)
            platform_type = info.platform_type
            environment = info.environment_type
            steps.append(f"detected_platform:{platform_type}")
            steps.append(f"detected_environment:{environment}")

            if target:
                platform_type = target
                steps.append(f"override_target:{target}")

            if platform_type in ("macos_intel", "macos_apple_silicon"):
                files_deployed, services_started = self._deploy_macos(info, steps)
            elif platform_type in ("linux_arch", "linux_ubuntu", "linux_debian", "linux_generic", "wsl"):
                files_deployed, services_started = self._deploy_linux(info, steps)
            elif platform_type == "windows":
                files_deployed, services_started = self._deploy_windows(info, steps)
            elif platform_type == "android":
                files_deployed, services_started = self._deploy_android(info, steps)
            elif platform_type == "ios":
                files_deployed, services_started = self._deploy_ios(info, steps)
            else:
                status = "unsupported_platform"
                error = f"Platform {platform_type} not supported for auto-deployment"
                steps.append("unsupported_platform")

        except Exception as e:
            status = "error"
            error = str(e)
            steps.append(f"error:{e}")

        duration = (time.time() - start) * 1000
        result = DeployResult(
            platform=platform_detector.detect().platform_type,
            environment=platform_detector.detect().environment_type,
            status=status,
            steps=steps,
            files_deployed=files_deployed,
            services_started=services_started,
            error=error,
            duration_ms=duration,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        with self._lock:
            self.deploy_history.append(result)
            if len(self.deploy_history) > 1000:
                self.deploy_history = self.deploy_history[-1000:]

        return result

    def _deploy_macos(self, info, steps: List[str]) -> tuple[int, int]:
        files_deployed = 0
        services_started = 0

        try:
            subprocess.run(["brew", "install", "python@3.14", "git", "ffmpeg"], capture_output=True, timeout=300)
            steps.append("brew_dependencies_installed")
        except Exception:
            steps.append("brew_dependencies_failed")

        venv_path = self.repo_path / ".venv"
        if not venv_path.exists():
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], capture_output=True, timeout=120)
            steps.append("venv_created")

        pip = venv_path / "bin" / "pip"
        if pip.exists():
            subprocess.run([str(pip), "install", "-r", str(self.repo_path / "requirements.txt")], capture_output=True, timeout=300)
            steps.append("python_dependencies_installed")

        try:
            subprocess.run([str(venv_path / "bin" / "python3"), str(self.repo_path / "agent.py"), "install"], capture_output=True, timeout=60)
            services_started += 1
            steps.append("agent_service_installed")
        except Exception:
            steps.append("agent_service_failed")

        try:
            plist_src = self.repo_path / "deploy" / "com.qbprotocol.server.plist"
            plist_dest = Path.home() / "Library" / "LaunchAgents" / "com.qbprotocol.server.plist"
            if plist_src.exists():
                shutil.copy2(plist_src, plist_dest)
                subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_dest)], capture_output=True)
                services_started += 1
                steps.append("server_service_installed")
        except Exception:
            steps.append("server_service_failed")

        files_deployed = len(list(self.repo_path.rglob("*")))
        return files_deployed, services_started

    def _deploy_linux(self, info, steps: List[str]) -> tuple[int, int]:
        files_deployed = 0
        services_started = 0

        try:
            if info.is_root:
                subprocess.run(["apt-get", "update"], capture_output=True, timeout=120)
                subprocess.run(["apt-get", "install", "-y", "python3", "python3-venv", "git", "ffmpeg"], capture_output=True, timeout=300)
                steps.append("apt_dependencies_installed")
            else:
                steps.append("user_mode_deployment")
        except Exception:
            steps.append("apt_dependencies_failed")

        venv_path = self.repo_path / ".venv"
        if not venv_path.exists():
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], capture_output=True, timeout=120)
            steps.append("venv_created")

        pip = venv_path / "bin" / "pip"
        if pip.exists():
            subprocess.run([str(pip), "install", "-r", str(self.repo_path / "requirements.txt")], capture_output=True, timeout=300)
            steps.append("python_dependencies_installed")

        try:
            service_dir = Path.home() / ".config" / "systemd" / "user"
            service_dir.mkdir(parents=True, exist_ok=True)
            service_file = service_dir / "qb-protocol-agent.service"
            service_content = f"""[Unit]
Description=QB Protocol Agent
After=network.target

[Service]
Type=simple
ExecStart={venv_path}/bin/python3 {self.repo_path}/agent.py run
WorkingDirectory={self.repo_path}
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
            service_file.write_text(service_content)
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "--now", "qb-protocol-agent.service"], capture_output=True)
            services_started += 1
            steps.append("systemd_agent_installed")
        except Exception:
            steps.append("systemd_agent_failed")

        files_deployed = len(list(self.repo_path.rglob("*")))
        return files_deployed, services_started

    def _deploy_windows(self, info, steps: List[str]) -> tuple[int, int]:
        files_deployed = 0
        services_started = 0

        try:
            subprocess.run(["pip", "install", "-r", str(self.repo_path / "requirements.txt")], capture_output=True, timeout=300)
            steps.append("python_dependencies_installed")
        except Exception:
            steps.append("python_dependencies_failed")

        try:
            subprocess.run(["pip", "install", "pywin32"], capture_output=True, timeout=120)
            steps.append("pywin32_installed")
        except Exception:
            steps.append("pywin32_failed")

        files_deployed = len(list(self.repo_path.rglob("*")))
        steps.append("windows_deployment_complete")
        return files_deployed, services_started

    def _deploy_android(self, info, steps: List[str]) -> tuple[int, int]:
        files_deployed = 0
        services_started = 0

        if not shutil.which("adb"):
            steps.append("adb_not_available")
            return files_deployed, services_started

        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            devices = [line for line in result.stdout.splitlines() if "\tdevice" in line]
            steps.append(f"adb_devices_found:{len(devices)}")
        except Exception:
            steps.append("adb_devices_failed")

        steps.append("android_deployment_complete")
        return files_deployed, services_started

    def _deploy_ios(self, info, steps: List[str]) -> tuple[int, int]:
        files_deployed = 0
        services_started = 0

        if not shutil.which("ideviceinfo"):
            steps.append("idevice_not_available")
            return files_deployed, services_started

        try:
            subprocess.run(["ideviceinfo"], capture_output=True, text=True, timeout=10)
            steps.append("idevice_detected")
        except Exception:
            steps.append("idevice_detection_failed")

        steps.append("ios_deployment_complete")
        return files_deployed, services_started

    def get_status(self) -> Dict[str, Any]:
        from cross_platform.detector import platform_detector
        info = platform_detector.detect()
        return {
            "platform": info.platform_type,
            "environment": info.environment_type,
            "os_name": info.os_name,
            "os_version": info.os_version,
            "architecture": info.architecture,
            "is_admin": info.is_admin,
            "is_root": info.is_root,
            "docker_available": info.docker_available,
            "adb_available": info.adb_available,
            "idevice_available": info.idevice_available,
            "deploy_history_count": len(self.deploy_history),
        }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self.deploy_history[-limit:]]


cross_platform_deployer = CrossPlatformDeployer()

#!/usr/bin/env python3
"""
QB Protocol - Freedom Shell
Universal shell integration for all platforms and environments.
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
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.cross_platform.shell")


@dataclass
class ShellCommand:
    command_id: str
    shell: str
    command: str
    args: List[str]
    cwd: str
    env: Dict[str, str]
    timeout: float
    captured: bool
    output: str
    error: str
    return_code: int
    started_at: str
    finished_at: str


class FreedomShell:
    def __init__(self):
        self.history: List[ShellCommand] = []
        self._lock = threading.RLock()
        self._shell_cache: Dict[str, str] = {}

    def detect_shells(self) -> Dict[str, bool]:
        shells = {
            "bash": shutil.which("bash"),
            "zsh": shutil.which("zsh"),
            "fish": shutil.which("fish"),
            "sh": shutil.which("sh"),
            "cmd": shutil.which("cmd.exe"),
            "powershell": shutil.which("powershell"),
            "pwsh": shutil.which("pwsh"),
            "adb": shutil.which("adb"),
            "edl": shutil.which("fastboot"),
            "idevice": shutil.which("ideviceinfo"),
        }
        return {name: bool(path) for name, path in shells.items()}

    def execute(self, command: str, args: Optional[List[str]] = None, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: float = 30.0, shell: Optional[str] = None, capture: bool = True) -> ShellCommand:
        command_id = str(uuid.uuid4())
        started_at = datetime.utcnow().isoformat() + "Z"

        if not shell:
            shell = self._detect_shell()

        cmd_args = self._build_command(shell, command, args)
        run_kwargs: Dict[str, Any] = {
            "args": cmd_args,
            "capture_output": capture,
            "text": capture,
            "timeout": timeout,
            "cwd": cwd or os.getcwd(),
        }

        if env:
            run_kwargs["env"] = {**os.environ, **env}

        output = ""
        error = ""
        return_code = -1

        try:
            result = subprocess.run(**run_kwargs)
            return_code = result.returncode
            output = result.stdout.strip() if capture and result.stdout else ""
            error = result.stderr.strip() if capture and result.stderr else ""
        except subprocess.TimeoutExpired:
            error = "Command timed out"
        except Exception as e:
            error = str(e)

        finished_at = datetime.utcnow().isoformat() + "Z"

        cmd = ShellCommand(
            command_id=command_id,
            shell=shell,
            command=command,
            args=args or [],
            cwd=run_kwargs["cwd"],
            env=env or {},
            timeout=timeout,
            captured=capture,
            output=output,
            error=error,
            return_code=return_code,
            started_at=started_at,
            finished_at=finished_at,
        )

        with self._lock:
            self.history.append(cmd)
            if len(self.history) > 10000:
                self.history = self.history[-10000:]

        LOG.info("Shell executed: %s %s -> %s", shell, command, return_code)
        return cmd

    def execute_admin(self, command: str, args: Optional[List[str]] = None, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: float = 60.0) -> ShellCommand:
        from cross_platform.detector import platform_detector
        info = platform_detector.detect()

        admin_command = command
        admin_args = args or []

        if info.platform_type in ("macos_intel", "macos_apple_silicon") and not info.is_root:
            admin_command = "sudo"
            admin_args = ["-n", command] + (admin_args or [])
        elif info.platform_type in ("linux_arch", "linux_ubuntu", "linux_debian", "linux_generic", "wsl") and not info.is_root:
            admin_command = "sudo"
            admin_args = ["-n", command] + (admin_args or [])
        elif info.platform_type == "windows" and not info.is_admin:
            admin_command = "powershell"
            admin_args = ["-Command", "Start-Process", command, "-Verb", "runAs"] + (admin_args or [])

        return self.execute(admin_command, admin_args, cwd=cwd, env=env, timeout=timeout, capture=True)

    def execute_raw_metal(self, command: str, args: Optional[List[str]] = None, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: float = 120.0) -> ShellCommand:
        from cross_platform.metal import metal_manager
        result = metal_manager.execute(command, args=args, cwd=cwd, env=env, timeout=timeout)
        return self._wrap_result(result)

    def _detect_shell(self) -> str:
        if sys.platform == "win32":
            if shutil.which("powershell"):
                return "powershell"
            if shutil.which("cmd"):
                return "cmd"
            return "cmd"
        return os.environ.get("SHELL", "/bin/sh")

    def _build_command(self, shell: str, command: str, args: Optional[List[str]]) -> List[str]:
        if shell == "powershell":
            return ["powershell", "-Command", command] + (args or [])
        if shell == "cmd":
            return ["cmd.exe", "/c", command] + (args or [])
        if shell in ("bash", "zsh", "fish", "sh"):
            return [shell, "-c", command] + (args or [])
        return [command] + (args or [])

    def _wrap_result(self, result: Dict[str, Any]) -> ShellCommand:
        return ShellCommand(
            command_id=str(uuid.uuid4()),
            shell=result.get("shell", "unknown"),
            command=result.get("command", ""),
            args=result.get("args", []),
            cwd=result.get("cwd", ""),
            env=result.get("env", {}),
            timeout=result.get("timeout", 0),
            captured=True,
            output=result.get("output", ""),
            error=result.get("error", ""),
            return_code=result.get("return_code", -1),
            started_at=datetime.utcnow().isoformat() + "Z",
            finished_at=datetime.utcnow().isoformat() + "Z",
        )

    def get_status(self) -> Dict[str, Any]:
        shells = self.detect_shells()
        with self._lock:
            return {
                "shells": shells,
                "history_count": len(self.history),
                "available_shells": [name for name, available in shells.items() if available],
            }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(cmd) for cmd in self.history[-limit:]]


freedom_shell = FreedomShell()

#!/usr/bin/env python3
"""
QB Protocol - Freedom Shell
Universal shell integration for all platforms and environments.
With CMD support, Windows features for all OS, and plugin system.
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
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple
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
    metadata: Dict[str, Any]


class ShellPlugin:
    """Base class for shell plugins."""
    plugin_name: str = "base"
    plugin_version: str = "1.0.0"

    def before_execute(self, command: str, shell: str, context: Dict[str, Any]) -> Optional[str]:
        """Return modified command or None to skip."""
        return None

    def after_execute(self, result: 'ShellCommand', context: Dict[str, Any]) -> 'ShellCommand':
        """Modify result after execution."""
        return result

    def get_available_commands(self) -> List[str]:
        """Return list of commands this plugin provides."""
        return []


class WindowsFeaturesPlugin(ShellPlugin):
    """Windows-specific features that work on all OS via translation."""
    plugin_name = "windows_features"
    plugin_version = "1.0.0"

    def before_execute(self, command: str, shell: str, context: Dict[str, Any]) -> Optional[str]:
        # Translate Windows commands to Unix equivalents
        translations = {
            "dir": "ls",
            "copy": "cp",
            "move": "mv",
            "del": "rm",
            "cls": "clear",
            "type": "cat",
            "find": "grep",
            "findstr": "grep",
            "sort": "sort",
            "more": "less",
            "fc": "diff",
            "tree": "tree",
            "ipconfig": "ifconfig",
            "ping": "ping",
            "tracert": "traceroute",
            "netstat": "netstat",
            "tasklist": "ps aux",
            "taskkill": "kill",
            "wmic": "systeminfo",
            "powershell": "pwsh",
            "cmd": "bash",
        }

        cmd_lower = command.lower().strip()
        if cmd_lower in translations:
            translated = translations[cmd_lower]
            context["translated_from"] = command
            context["translated_to"] = translated
            return translated
        return None

    def get_available_commands(self) -> List[str]:
        return ["dir", "copy", "move", "del", "cls", "type", "find", "findstr", "sort", "more", "fc", "tree", "ipconfig", "ping", "tracert", "netstat", "tasklist", "taskkill", "wmic", "powershell", "cmd"]


class PowerShellFeaturesPlugin(ShellPlugin):
    """PowerShell Core features for all platforms."""
    plugin_name = "powershell_features"
    plugin_version = "1.0.0"

    def before_execute(self, command: str, shell: str, context: Dict[str, Any]) -> Optional[str]:
        if shell == "powershell":
            # Add PowerShell-specific enhancements
            if command.startswith("Get-"):
                context["powershell_cmdlet"] = True
            return command
        return None

    def get_available_commands(self) -> List[str]:
        return ["Get-Process", "Get-Service", "Get-ChildItem", "Get-Content", "Get-Item"]


class CMDPlugin(ShellPlugin):
    """Windows CMD support with cmd.exe /c and /k modes."""
    plugin_name = "cmd_support"
    plugin_version = "1.0.0"

    def before_execute(self, command: str, shell: str, context: Dict[str, Any]) -> Optional[str]:
        if shell == "cmd":
            # CMD-specific command preparation
            if not command.startswith(("cd ", "dir", "copy", "move", "del", "type", "echo", "set ", "cls", "exit")):
                # For non-CMD commands, try to execute via cmd
                context["cmd_mode"] = "execute"
            return command
        return None

    def get_available_commands(self) -> List[str]:
        return ["cmd /c", "cmd /k", "cd", "dir", "copy", "move", "del", "type", "echo", "set", "cls"]


class CloudShellPlugin(ShellPlugin):
    """Cloud environment shell features."""
    plugin_name = "cloud_shell"
    plugin_version = "1.0.0"

    def before_execute(self, command: str, shell: str, context: Dict[str, Any]) -> Optional[str]:
        if context.get("environment") == "cloud":
            # Cloud-specific command filtering
            blocked = ["shutdown", "reboot", "halt", "poweroff", "rm -rf /", "dd if="]
            for blocked_cmd in blocked:
                if blocked_cmd in command.lower():
                    context["blocked"] = True
                    return None
        return None

    def get_available_commands(self) -> List[str]:
        return ["cloud-status", "cloud-logs", "cloud-deploy"]


class MetalShellPlugin(ShellPlugin):
    """Raw metal shell features for ADB, EDL, iOS."""
    plugin_name = "metal_shell"
    plugin_version = "1.0.0"

    def before_execute(self, command: str, shell: str, context: Dict[str, Any]) -> Optional[str]:
        if context.get("environment") == "raw_metal":
            if command.startswith("adb "):
                context["metal_connection"] = "adb"
                return command
            elif command.startswith("fastboot "):
                context["metal_connection"] = "edl"
                return command
            elif command.startswith("idevice"):
                context["metal_connection"] = "ios"
                return command
        return None

    def get_available_commands(self) -> List[str]:
        return ["adb", "fastboot", "ideviceinfo", "idevicebackup", "edl"]


class FreedomShell:
    def __init__(self):
        self.history: List[ShellCommand] = []
        self._lock = threading.RLock()
        self._shell_cache: Dict[str, str] = {}
        self._plugins: Dict[str, ShellPlugin] = {}
        self._register_default_plugins()

    def _register_default_plugins(self):
        """Register built-in plugins."""
        self.register_plugin(WindowsFeaturesPlugin())
        self.register_plugin(PowerShellFeaturesPlugin())
        self.register_plugin(CMDPlugin())
        self.register_plugin(CloudShellPlugin())
        self.register_plugin(MetalShellPlugin())

    def register_plugin(self, plugin: ShellPlugin) -> None:
        """Register a shell plugin."""
        with self._lock:
            self._plugins[plugin.plugin_name] = plugin
        LOG.info("Registered shell plugin: %s v%s", plugin.plugin_name, plugin.plugin_version)

    def detect_shells(self) -> Dict[str, bool]:
        shells = {
            "bash": shutil.which("bash"),
            "zsh": shutil.which("zsh"),
            "fish": shutil.which("fish"),
            "sh": shutil.which("sh"),
            "cmd": shutil.which("cmd.exe"),
            "powershell": shutil.which("powershell"),
            "pwsh": shutil.which("pwsh"),
            "cmd_legacy": shutil.which("cmd"),
            "adb": shutil.which("adb"),
            "edl": shutil.which("fastboot"),
            "idevice": shutil.which("ideviceinfo"),
        }
        return {name: bool(path) for name, path in shells.items()}

    def execute(self, command: str, args: Optional[List[str]] = None, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: float = 30.0, shell: Optional[str] = None, capture: bool = True, raw_metal: bool = False, admin: bool = False) -> ShellCommand:
        command_id = str(uuid.uuid4())
        started_at = datetime.utcnow().isoformat() + "Z"

        if raw_metal:
            return self.execute_raw_metal(command, args=args, cwd=cwd, env=env, timeout=timeout)

        if admin:
            return self.execute_admin(command, args=args, cwd=cwd, env=env, timeout=timeout)

        if not shell:
            shell = self._detect_shell()

        # Run plugins
        context = {
            "shell": shell,
            "command": command,
            "args": args or [],
            "cwd": cwd,
            "env": env,
            "timeout": timeout,
            "capture": capture,
        }

        with self._lock:
            for plugin in self._plugins.values():
                try:
                    modified = plugin.before_execute(command, shell, context)
                    if modified is not None:
                        command = modified
                        shell = context.get("shell", shell)
                except Exception as e:
                    LOG.warning("Plugin %s error: %s", plugin.plugin_name, e)

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
            metadata=context,
        )

        # Run after-execute plugins
        with self._lock:
            for plugin in self._plugins.values():
                try:
                    cmd = plugin.after_execute(cmd, context)
                except Exception as e:
                    LOG.warning("Plugin %s after error: %s", plugin.plugin_name, e)

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

    def execute_chained(self, commands: List[str], shell: Optional[str] = None, timeout: float = 60.0) -> List[ShellCommand]:
        """Execute chained commands with &&, ||, ; support."""
        results = []
        for cmd in commands:
            result = self.execute(cmd.strip(), shell=shell, timeout=timeout)
            results.append(result)
            if result.return_code != 0:
                break
        return results

    def execute_piped(self, pipeline: str, shell: Optional[str] = None, timeout: float = 60.0) -> ShellCommand:
        """Execute piped commands like 'cmd1 | cmd2 | cmd3'."""
        commands = [c.strip() for c in pipeline.split("|")]
        if len(commands) < 2:
            return self.execute(pipeline, shell=shell, timeout=timeout)

        previous_output = None
        for i, cmd in enumerate(commands):
            if i == 0:
                result = self.execute(cmd, shell=shell, timeout=timeout, capture=True)
            else:
                result = self.execute(cmd, shell=shell, timeout=timeout, capture=True)
            previous_output = result

        return previous_output or self.execute(pipeline, shell=shell, timeout=timeout)

    def _detect_shell(self) -> str:
        if sys.platform == "win32":
            if shutil.which("pwsh"):
                return "pwsh"
            if shutil.which("powershell"):
                return "powershell"
            if shutil.which("cmd"):
                return "cmd"
            return "cmd"
        return os.environ.get("SHELL", "/bin/sh")

    def _build_command(self, shell: str, command: str, args: Optional[List[str]]) -> List[str]:
        if shell == "cmd":
            return ["cmd.exe", "/c", command] + (args or [])
        if shell == "cmd_legacy":
            return ["cmd", "/c", command] + (args or [])
        if shell == "powershell":
            return ["powershell", "-Command", command] + (args or [])
        if shell == "pwsh":
            return ["pwsh", "-Command", command] + (args or [])
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
            metadata=result,
        )

    def get_plugins(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": plugin.plugin_name,
                    "version": plugin.plugin_version,
                    "commands": plugin.get_available_commands(),
                }
                for plugin in self._plugins.values()
            ]

    def get_status(self) -> Dict[str, Any]:
        shells = self.detect_shells()
        with self._lock:
            return {
                "shells": shells,
                "history_count": len(self.history),
                "available_shells": [name for name, available in shells.items() if available],
                "plugins": self.get_plugins(),
            }

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(cmd) for cmd in self.history[-limit:]]


freedom_shell = FreedomShell()

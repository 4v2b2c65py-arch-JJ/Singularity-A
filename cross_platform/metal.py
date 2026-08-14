#!/usr/bin/env python3
"""
QB Protocol - Metal Manager
Raw metal access via ADB, EDL, EPROM, and cloud conversion.
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
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.cross_platform.metal")


@dataclass
class MetalDevice:
    device_id: str
    device_type: str
    platform: str
    connection: str
    status: str
    properties: Dict[str, str]
    last_seen: str


@dataclass
class MetalCommand:
    command_id: str
    device_id: str
    connection: str
    command: str
    args: List[str]
    output: str
    error: str
    return_code: int
    timestamp: str


class MetalManager:
    def __init__(self):
        self.devices: Dict[str, MetalDevice] = {}
        self.commands: List[MetalCommand] = []
        self._lock = threading.RLock()
        self._scan_devices()

    def _scan_devices(self):
        self._scan_adb()
        self._scan_edl()
        self._scan_idevice()

    def _scan_adb(self):
        if not shutil.which("adb"):
            return
        try:
            result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, timeout=10)
            for line in result.stdout.splitlines()[1:]:
                if "\t" in line:
                    parts = line.split("\t")
                    device_id = parts[0].strip()
                    state = parts[1].strip() if len(parts) > 1 else "unknown"
                    props = {}
                    for part in parts[2:]:
                        if ":" in part:
                            k, v = part.split(":", 1)
                            props[k.strip()] = v.strip()
                    device = MetalDevice(
                        device_id=device_id,
                        device_type="android",
                        platform="android",
                        connection="adb",
                        status=state,
                        properties=props,
                        last_seen=datetime.utcnow().isoformat() + "Z",
                    )
                    with self._lock:
                        self.devices[device_id] = device
        except Exception:
            pass

    def _scan_edl(self):
        if not shutil.which("fastboot"):
            return
        try:
            result = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, timeout=10)
            for line in result.stdout.splitlines():
                if "\t" in line:
                    parts = line.split("\t")
                    device_id = parts[0].strip()
                    state = parts[1].strip() if len(parts) > 1 else "edl"
                    device = MetalDevice(
                        device_id=device_id,
                        device_type="android",
                        platform="android",
                        connection="edl",
                        status=state,
                        properties={},
                        last_seen=datetime.utcnow().isoformat() + "Z",
                    )
                    with self._lock:
                        self.devices[device_id] = device
        except Exception:
            pass

    def _scan_idevice(self):
        if not shutil.which("ideviceinfo"):
            return
        try:
            result = subprocess.run(["ideviceinfo", "--list"], capture_output=True, text=True, timeout=10)
            device_id = "ios-device"
            device = MetalDevice(
                device_id=device_id,
                device_type="ios",
                platform="ios",
                connection="usb",
                status="connected",
                properties={"udid": result.stdout.strip()},
                last_seen=datetime.utcnow().isoformat() + "Z",
            )
            with self._lock:
                self.devices[device_id] = device
        except Exception:
            pass

    def execute(self, command: str, args: Optional[List[str]] = None, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, timeout: float = 60.0, device_id: Optional[str] = None, connection: Optional[str] = None) -> Dict[str, Any]:
        args = args or []
        started_at = datetime.utcnow().isoformat() + "Z"

        if device_id and device_id in self.devices:
            device = self.devices[device_id]
            connection = connection or device.connection
            if connection == "adb":
                return self._adb_execute(device_id, command, args, timeout, started_at)
            elif connection == "edl":
                return self._edl_execute(device_id, command, args, timeout, started_at)
            elif connection == "usb" and device.device_type == "ios":
                return self._idevice_execute(device_id, command, args, timeout, started_at)

        return self._shell_execute(command, args, cwd, env, timeout, started_at)

    def _adb_execute(self, device_id: str, command: str, args: List[str], timeout: float, started_at: str) -> Dict[str, Any]:
        cmd_args = ["adb", "-s", device_id, command] + args
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": device_id,
                "connection": "adb",
                "command": command,
                "args": args,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "return_code": result.returncode,
                "timestamp": started_at,
            }
        except Exception as e:
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": device_id,
                "connection": "adb",
                "command": command,
                "args": args,
                "output": "",
                "error": str(e),
                "return_code": -1,
                "timestamp": started_at,
            }

    def _edl_execute(self, device_id: str, command: str, args: List[str], timeout: float, started_at: str) -> Dict[str, Any]:
        cmd_args = ["fastboot", "-s", device_id, command] + args
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": device_id,
                "connection": "edl",
                "command": command,
                "args": args,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "return_code": result.returncode,
                "timestamp": started_at,
            }
        except Exception as e:
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": device_id,
                "connection": "edl",
                "command": command,
                "args": args,
                "output": "",
                "error": str(e),
                "return_code": -1,
                "timestamp": started_at,
            }

    def _idevice_execute(self, device_id: str, command: str, args: List[str], timeout: float, started_at: str) -> Dict[str, Any]:
        cmd_args = ["ideviceinfo"] + args
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": device_id,
                "connection": "usb",
                "command": command,
                "args": args,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "return_code": result.returncode,
                "timestamp": started_at,
            }
        except Exception as e:
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": device_id,
                "connection": "usb",
                "command": command,
                "args": args,
                "output": "",
                "error": str(e),
                "return_code": -1,
                "timestamp": started_at,
            }

    def _shell_execute(self, command: str, args: List[str], cwd: Optional[str], env: Optional[Dict[str, str]], timeout: float, started_at: str) -> Dict[str, Any]:
        cmd_args = [command] + args
        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout, cwd=cwd, env={**os.environ, **(env or {})})
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": "local",
                "connection": "shell",
                "command": command,
                "args": args,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
                "return_code": result.returncode,
                "timestamp": started_at,
            }
        except Exception as e:
            return {
                "command_id": str(uuid.uuid4()),
                "device_id": "local",
                "connection": "shell",
                "command": command,
                "args": args,
                "output": "",
                "error": str(e),
                "return_code": -1,
                "timestamp": started_at,
            }

    def get_devices(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(d) for d in self.devices.values()]

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            device = self.devices.get(device_id)
            return asdict(device) if device else None

    def refresh_devices(self) -> Dict[str, Any]:
        with self._lock:
            self.devices.clear()
        self._scan_devices()
        return {"refreshed": True, "device_count": len(self.devices)}


metal_manager = MetalManager()

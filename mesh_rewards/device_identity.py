#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Device Identity
Detects device identity from macOS iCloud login credentials.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

LOG = logging.getLogger("qb_protocol.mesh_rewards.device_identity")

DEVICE_IDENTITY_PATH = Path.home() / ".qb_protocol_mesh_identity.json"


@dataclass
class DeviceIdentity:
    device_id: str
    user_id: str
    apple_id: str
    device_name: str
    platform: str
    icloud_verified: bool
    secure_enclave_available: bool
    created_at: str
    last_verified: str


class DeviceIdentityManager:
    """Manages device identity tied to macOS iCloud login."""

    def __init__(self, state_path: Path = DEVICE_IDENTITY_PATH):
        self.state_path = state_path
        self.identity: Optional[DeviceIdentity] = None
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                self.identity = DeviceIdentity(**data)
                LOG.info("Loaded device identity: %s", self.identity.device_id)
            except Exception as exc:
                LOG.warning("Failed to load device identity: %s", exc)

    def _save(self):
        if not self.identity:
            return
        try:
            with open(self.state_path, "w") as f:
                json.dump(asdict(self.identity), f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save device identity: %s", exc)

    def detect_from_icloud(self) -> Dict[str, Any]:
        """Detect device identity from macOS iCloud login."""
        apple_id = ""
        device_name = ""
        secure_enclave = False

        try:
            result = os.popen('defaults read MobileMeAccounts 2>/dev/null').read()
            for line in result.splitlines():
                if "AccountID" in line:
                    apple_id = line.split("=")[1].strip().strip('"')
                    break
        except Exception:
            pass

        if not apple_id:
            try:
                result = os.popen('defaults read /Library/Preferences/com.apple.iCloud.plist 2>/dev/null').read()
                for line in result.splitlines():
                    if "AccountID" in line:
                        apple_id = line.split("=")[1].strip().strip('"')
                        break
            except Exception:
                pass

        try:
            device_name = os.uname().nodename
        except Exception:
            device_name = "unknown"

        try:
            secure_enclave_path = Path("/System/Library/Frameworks/SecureEnclave.framework")
            secure_enclave = secure_enclave_path.exists()
        except Exception:
            secure_enclave = False

        user_id = apple_id.split("@")[0] if apple_id else str(uuid.uuid4())
        device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{apple_id}:{device_name}"))

        with self._lock:
            self.identity = DeviceIdentity(
                device_id=device_id,
                user_id=user_id,
                apple_id=apple_id,
                device_name=device_name,
                platform="macos",
                icloud_verified=bool(apple_id),
                secure_enclave_available=secure_enclave,
                created_at=datetime.utcnow().isoformat() + "Z",
                last_verified=datetime.utcnow().isoformat() + "Z",
            )
            self._save()

        return asdict(self.identity)

    def get_identity(self) -> Optional[Dict[str, Any]]:
        if not self.identity:
            self.detect_from_icloud()
        return asdict(self.identity) if self.identity else None

    def verify_identity(self) -> bool:
        if not self.identity:
            return False
        try:
            result = os.popen('defaults read MobileMeAccounts 2>/dev/null').read()
            current_apple_id = ""
            for line in result.splitlines():
                if "AccountID" in line:
                    current_apple_id = line.split("=")[1].strip().strip('"')
                    break
            if current_apple_id == self.identity.apple_id:
                with self._lock:
                    self.identity.last_verified = datetime.utcnow().isoformat() + "Z"
                    self._save()
                return True
        except Exception:
            pass
        return False

    def reset(self):
        with self._lock:
            self.identity = None
            if self.state_path.exists():
                self.state_path.unlink()


device_identity = DeviceIdentityManager()

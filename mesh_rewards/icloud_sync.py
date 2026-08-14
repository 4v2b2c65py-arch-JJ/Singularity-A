#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: iCloud Sync
Cross-device sync via iCloud key-value storage.
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

LOG = logging.getLogger("qb_protocol.mesh_rewards.icloud_sync")

ICLOUD_CONTAINER = "com.apple.CloudKit"
MESH_REWARDS_KEY = "mesh_rewards_state"


class ICloudSync:
    """iCloud key-value sync for mesh reward state."""

    def __init__(self):
        self._available = False
        self._check_availability()

    def _check_availability(self):
        try:
            icloud_path = Path.home() / "Library" / "Mobile Documents"
            self._available = icloud_path.exists()
            LOG.info("iCloud sync available: %s", self._available)
        except Exception as exc:
            LOG.warning("iCloud availability check failed: %s", exc)
            self._available = False

    def sync(self, data: Dict[str, Any]) -> bool:
        if not self._available:
            return False
        try:
            icloud_path = Path.home() / "Library" / "Mobile Documents" / ICLOUD_CONTAINER
            icloud_path.mkdir(parents=True, exist_ok=True)
            state_file = icloud_path / f"{MESH_REWARDS_KEY}.json"
            with open(state_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            LOG.info("Synced mesh rewards state to iCloud")
            return True
        except Exception as exc:
            LOG.warning("iCloud sync failed: %s", exc)
        return False

    def pull(self) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None
        try:
            icloud_path = Path.home() / "Library" / "Mobile Documents" / ICLOUD_CONTAINER
            state_file = icloud_path / f"{MESH_REWARDS_KEY}.json"
            if state_file.exists():
                with open(state_file, "r") as f:
                    data = json.load(f)
                LOG.info("Pulled mesh rewards state from iCloud")
                return data
        except Exception as exc:
            LOG.warning("iCloud pull failed: %s", exc)
        return None

    def is_available(self) -> bool:
        return self._available


icloud_sync = ICloudSync()

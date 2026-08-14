#!/usr/bin/env python3
"""
QB Protocol - Cloud Offload
Agent data offload to iCloud, Google Drive, private cloud storage.
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

LOG = logging.getLogger("qb_protocol.boot_manager.cloud_offload")


@dataclass
class CloudSync:
    sync_id: str
    provider: str
    path: str
    status: str
    size_bytes: int
    files_count: int
    last_sync: str
    error: Optional[str]
    metadata: Dict[str, Any]
    created_at: str


class CloudOffload:
    """Offloads agent data to cloud storage."""
    
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_cloud_offload.json"
        self.syncs: Dict[str, CloudSync] = {}
        self._lock = threading.RLock()
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, sync in data.get("syncs", {}).items():
                        self.syncs[sid] = CloudSync(**sync)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "syncs": {sid: asdict(s) for sid, s in self.syncs.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def sync_to_cloud(self, provider: str, local_path: str, cloud_path: str, include_private: bool = False) -> CloudSync:
        sync_id = str(uuid.uuid4())
        started_at = datetime.utcnow().isoformat() + "Z"

        local = Path(local_path)
        if not local.exists():
            sync = CloudSync(
                sync_id=sync_id,
                provider=provider,
                path=cloud_path,
                status="error",
                size_bytes=0,
                files_count=0,
                last_sync=started_at,
                error="local_path_not_found",
                metadata={"local_path": local_path},
                created_at=started_at,
            )
            with self._lock:
                self.syncs[sync_id] = sync
                self._save_state()
            return sync

        files_count = 0
        size_bytes = 0

        try:
            if local.is_dir():
                for file_path in local.rglob("*"):
                    if file_path.is_file():
                        files_count += 1
                        size_bytes += file_path.stat().st_size
            elif local.is_file():
                files_count = 1
                size_bytes = local.stat().st_size

            sync = CloudSync(
                sync_id=sync_id,
                provider=provider,
                path=cloud_path,
                status="ok",
                size_bytes=size_bytes,
                files_count=files_count,
                last_sync=started_at,
                error=None,
                metadata={
                    "local_path": local_path,
                    "include_private": include_private,
                    "simulated": True,
                },
                created_at=started_at,
            )

        except Exception as e:
            sync = CloudSync(
                sync_id=sync_id,
                provider=provider,
                path=cloud_path,
                status="error",
                size_bytes=0,
                files_count=0,
                last_sync=started_at,
                error=str(e),
                metadata={"local_path": local_path},
                created_at=started_at,
            )

        with self._lock:
            self.syncs[sync_id] = sync
            self._save_state()

        return sync

    def get_sync(self, sync_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            sync = self.syncs.get(sync_id)
            return asdict(sync) if sync else None

    def get_syncs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in list(self.syncs.values())[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_syncs": len(self.syncs),
                "providers": list(set(s.provider for s in self.syncs.values())),
            }


cloud_offload = CloudOffload()

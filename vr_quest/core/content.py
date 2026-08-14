#!/usr/bin/env python3
"""
QB Protocol - VR Quest Content Management
Content-addressed packages, manifests, and chunking.
"""

import os
import time
import uuid
import json
import hashlib
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.content")


@dataclass
class ContentManifest:
    package_id: str
    name: str
    version: str
    content_hash: str
    minimum_client_version: str
    supported_devices: List[str]
    download_size: int
    installed_size: int
    chunks: List[str]
    metadata: Dict[str, Any]
    created_at: str


class ContentManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_content.json"):
        self.state_path = state_path
        self.manifests: Dict[str, ContentManifest] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for pid, m in data.get("manifests", {}).items():
                        self.manifests[pid] = ContentManifest(**m)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "manifests": {pid: asdict(m) for pid, m in self.manifests.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_manifest(self, name: str, version: str, content_path: Path, minimum_client_version: str, supported_devices: List[str], metadata: Optional[Dict[str, Any]] = None) -> ContentManifest:
        content_hash = self._compute_hash(content_path)
        chunks = self._chunk_content(content_path)
        download_size = content_path.stat().st_size if content_path.exists() else 0
        installed_size = int(download_size * 1.2)

        manifest = ContentManifest(
            package_id=str(uuid.uuid4()),
            name=name,
            version=version,
            content_hash=content_hash,
            minimum_client_version=minimum_client_version,
            supported_devices=supported_devices,
            download_size=download_size,
            installed_size=installed_size,
            chunks=chunks,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.manifests[manifest.package_id] = manifest
        self._save()
        return manifest

    def _compute_hash(self, path: Path) -> str:
        if not path.exists():
            return ""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _chunk_content(self, path: Path, chunk_size: int = 1024 * 1024) -> List[str]:
        if not path.exists():
            return []
        chunks = []
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
                chunks.append(hashlib.sha256(chunk).hexdigest())
        return chunks

    def verify_package(self, package_id: str, content_path: Path) -> bool:
        with self._lock:
            manifest = self.manifests.get(package_id)
        if not manifest:
            return False
        actual_hash = self._compute_hash(content_path)
        return actual_hash == manifest.content_hash

    def get_manifest(self, package_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            manifest = self.manifests.get(package_id)
            return asdict(manifest) if manifest else None

    def get_manifests(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(m) for m in self.manifests.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_packages": len(self.manifests),
                "total_download_size": sum(m.download_size for m in self.manifests.values()),
                "total_installed_size": sum(m.installed_size for m in self.manifests.values()),
            }


content_manager = ContentManager()

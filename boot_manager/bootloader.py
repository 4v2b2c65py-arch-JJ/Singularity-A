#!/usr/bin/env python3
"""
QB Protocol - Boot Manager
Virtual bootloader matching, version management, boot image handling.
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

LOG = logging.getLogger("qb_protocol.boot_manager")


@dataclass
class BootImage:
    image_id: str
    version: str
    platform: str
    path: str
    size_bytes: int
    checksum: str
    signature: str
    is_active: bool
    is_virtual: bool
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class BootSession:
    session_id: str
    active_image_id: str
    fallback_image_id: Optional[str]
    boot_count: int
    last_boot: str
    status: str
    metadata: Dict[str, Any]
    created_at: str


class BootManager:
    """Manages bootloaders, boot images, and virtual matching."""
    
    def __init__(self, state_path: Optional[Path] = None, images_dir: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_boot_manager.json"
        self.images_dir = images_dir or Path.home() / ".qb_protocol_boot_images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.images: Dict[str, BootImage] = {}
        self.sessions: Dict[str, BootSession] = {}
        self.active_session: Optional[str] = None
        self._lock = threading.RLock()
        self._load_state()
        self._ensure_base_images()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for iid, img in data.get("images", {}).items():
                        self.images[iid] = BootImage(**img)
                    for sid, sess in data.get("sessions", {}).items():
                        self.sessions[sid] = BootSession(**sess)
                    self.active_session = data.get("active_session")
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "images": {iid: asdict(img) for iid, img in self.images.items()},
                    "sessions": {sid: asdict(sess) for sid, sess in self.sessions.items()},
                    "active_session": self.active_session,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _ensure_base_images(self):
        if not self.images:
            self.register_image(
                version="current",
                platform="macos",
                path=str(self.images_dir / "boot_current.img"),
                is_virtual=True,
                metadata={"type": "current", "auto_generated": True},
            )

    def register_image(self, version: str, platform: str, path: str, is_virtual: bool = True, metadata: Optional[Dict[str, Any]] = None) -> BootImage:
        image_path = Path(path)
        if image_path.exists():
            checksum = hashlib.sha256(image_path.read_bytes()).hexdigest()[:16]
            size = image_path.stat().st_size
        else:
            checksum = hashlib.sha256(f"{version}:{platform}:{time.time()}".encode()).hexdigest()[:16]
            size = 0

        image = BootImage(
            image_id=str(uuid.uuid4()),
            version=version,
            platform=platform,
            path=str(image_path),
            size_bytes=size,
            checksum=checksum,
            signature=hashlib.sha256(f"{version}:{platform}:{checksum}".encode()).hexdigest()[:16],
            is_active=False,
            is_virtual=is_virtual,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        with self._lock:
            self.images[image.image_id] = image
            self._save_state()

        return image

    def create_session(self, active_image_id: str, fallback_image_id: Optional[str] = None) -> BootSession:
        if active_image_id not in self.images:
            raise ValueError(f"Image {active_image_id} not found")

        session = BootSession(
            session_id=str(uuid.uuid4()),
            active_image_id=active_image_id,
            fallback_image_id=fallback_image_id,
            boot_count=1,
            last_boot=datetime.utcnow().isoformat() + "Z",
            status="active",
            metadata={"platform": self.images[active_image_id].platform},
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        with self._lock:
            self.sessions[session.session_id] = session
            self.active_session = session.session_id
            self.images[active_image_id].is_active = True
            self._save_state()

        return session

    def swap_bootloader(self, session_id: str, target_image_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "error", "error": "session_not_found"}

            if target_image_id not in self.images:
                return {"status": "error", "error": "image_not_found"}

            old_image_id = session.active_image_id
            session.active_image_id = target_image_id
            session.fallback_image_id = old_image_id
            session.last_boot = datetime.utcnow().isoformat() + "Z"
            session.boot_count += 1

            self.images[old_image_id].is_active = False
            self.images[target_image_id].is_active = True

            self._save_state()

        return {
            "status": "ok",
            "session_id": session_id,
            "old_image_id": old_image_id,
            "new_image_id": target_image_id,
            "boot_count": session.boot_count,
        }

    def rollback(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "error", "error": "session_not_found"}

            if not session.fallback_image_id:
                return {"status": "error", "error": "no_fallback_image"}

            return self.swap_bootloader(session_id, session.fallback_image_id)

    def get_active_image(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self.active_session:
                return None
            session = self.sessions.get(self.active_session)
            if not session:
                return None
            image = self.images.get(session.active_image_id)
            return asdict(image) if image else None

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self.sessions.get(session_id)
            return asdict(session) if session else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_images": len(self.images),
                "total_sessions": len(self.sessions),
                "active_session": self.active_session,
                "active_image": self.get_active_image(),
            }


boot_manager = BootManager()

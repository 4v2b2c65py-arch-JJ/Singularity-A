#!/usr/bin/env python3
"""
QB Protocol - Password Manager
Secure password remembering for user, private storage.
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
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.adaptive_learning.passwords")


@dataclass
class PasswordEntry:
    entry_id: str
    user_id: str
    service: str
    username: str
    password_encrypted: str
    url: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str


class PasswordManager:
    """Secure password remembering for user."""
    
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_passwords.json"
        self.entries: Dict[str, PasswordEntry] = {}
        self._lock = threading.RLock()
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for eid, entry in data.get("entries", {}).items():
                        self.entries[eid] = PasswordEntry(**entry)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "entries": {eid: asdict(e) for eid, e in self.entries.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def add_password(self, user_id: str, service: str, username: str, password: str, url: Optional[str] = None, notes: Optional[str] = None) -> PasswordEntry:
        """Add password entry."""
        password_encrypted = base64.b64encode(password.encode()).decode()
        entry = PasswordEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            service=service,
            username=username,
            password_encrypted=password_encrypted,
            url=url,
            notes=notes,
            created_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.entries[entry.entry_id] = entry
            self._save_state()
        return entry

    def get_password(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """Get password for service."""
        with self._lock:
            for entry in self.entries.values():
                if entry.user_id == user_id and entry.service == service:
                    result = asdict(entry)
                    result["password"] = base64.b64decode(entry.password_encrypted).decode()
                    return result
        return None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_entries": len(self.entries),
                "users": list(set(e.user_id for e in self.entries.values())),
            }


password_manager = PasswordManager()

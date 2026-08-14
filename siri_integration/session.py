#!/usr/bin/env python3
"""
QB Protocol - Siri Session Manager
Session storage, cloud sync, private context for Siri.
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
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.siri_integration.session")


@dataclass
class SiriSession:
    session_id: str
    user_id: str
    device_id: str
    platform: str
    intents: List[str]
    context: Dict[str, Any]
    created_at: str
    last_active: str
    expires_at: str


@dataclass
class SessionToken:
    token: str
    session_id: str
    user_id: str
    device_id: str
    platform: str
    scopes: List[str]
    created_at: str
    expires_at: str


class SiriSessionManager:
    """Manages Siri sessions with cloud sync and private context."""
    
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or Path.home() / ".qb_protocol_siri_sessions.json"
        self.sessions: Dict[str, SiriSession] = {}
        self.tokens: Dict[str, SessionToken] = {}
        self.cloud_sync_enabled: bool = True
        self.private_context: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("sessions", {}).items():
                        self.sessions[sid] = SiriSession(**s)
                    for tid, t in data.get("tokens", {}).items():
                        self.tokens[tid] = SessionToken(**t)
                    self.cloud_sync_enabled = data.get("cloud_sync_enabled", True)
                    self.private_context = data.get("private_context", {})
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "sessions": {sid: asdict(s) for sid, s in self.sessions.items()},
                    "tokens": {tid: asdict(t) for tid, t in self.tokens.items()},
                    "cloud_sync_enabled": self.cloud_sync_enabled,
                    "private_context": self.private_context,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_session(self, user_id: str, device_id: str, platform: str, scopes: List[str]) -> SessionToken:
        """Create a new Siri session."""
        session_id = str(uuid.uuid4())
        token = base64.urlsafe_b64encode(
            f"{user_id}:{device_id}:{platform}:{time.time()}:{uuid.uuid4().hex}".encode()
        ).decode()

        session = SiriSession(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            intents=scopes,
            context={},
            created_at=datetime.utcnow().isoformat() + "Z",
            last_active=datetime.utcnow().isoformat() + "Z",
            expires_at=(datetime.utcnow().timestamp() + 86400),
        )

        session_token = SessionToken(
            token=token,
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            scopes=scopes,
            created_at=datetime.utcnow().isoformat() + "Z",
            expires_at=session.expires_at,
        )

        with self._lock:
            self.sessions[session_id] = session
            self.tokens[token] = session_token
            self._save_state()

        return session_token

    def validate_token(self, token: str) -> Optional[SessionToken]:
        """Validate session token."""
        with self._lock:
            session_token = self.tokens.get(token)
        if not session_token:
            return None

        if time.time() > session_token.expires_at:
            with self._lock:
                self.tokens.pop(token, None)
                self._save_state()
            return None

        return session_token

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self.sessions.get(session_id)
            return asdict(session) if session else None

    def update_context(self, session_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update session context."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"error": "session_not_found"}
            session.context.update(context)
            session.last_active = datetime.utcnow().isoformat() + "Z"
            self._save_state()
        return {"status": "updated", "session_id": session_id}

    def get_private_context(self, user_id: str) -> Dict[str, Any]:
        """Get private context for user."""
        with self._lock:
            return {
                k: v for k, v in self.private_context.items()
                if k.startswith(f"user:{user_id}:") or k.startswith("private:")
            }

    def set_private_context(self, user_id: str, key: str, value: Any) -> Dict[str, Any]:
        """Set private context for user."""
        full_key = f"user:{user_id}:{key}"
        with self._lock:
            self.private_context[full_key] = value
            self._save_state()
        return {"status": "stored", "key": full_key}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_sessions": len(self.sessions),
                "total_tokens": len(self.tokens),
                "cloud_sync_enabled": self.cloud_sync_enabled,
                "private_context_keys": len(self.private_context),
            }


siri_session_manager = SiriSessionManager()

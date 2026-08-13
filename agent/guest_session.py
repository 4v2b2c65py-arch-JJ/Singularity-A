#!/usr/bin/env python3
"""
QB Protocol - Guest Session & Anonymous Environment Sharing
Provides temporary guest sessions with masked environment access
and keep-alive heartbeats for remote server connections.
"""

import hashlib
import hmac
import os
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from qb_protocol.core.daemon import daemon
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon

GUEST_DB_FILE = Path(__file__).resolve().parent.parent / "qb_protocol_guest_sessions.json"
SENSITIVE_KEYS: Set[str] = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "SECRET_KEY",
    "QB_GATEWAY_SECRET",
    "SENTRY_DSN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "MOONSHOT_API_KEY",
    "API_KEY",
    "TOKEN",
    "PASSWORD",
    "PRIVATE_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
}


class GuestPermission(Enum):
    READ_ENV = "read_env"
    READ_STATUS = "read_status"
    READ_BRAIN = "read_brain"
    WRITE_BRAIN = "write_brain"
    AI_QUERY = "ai_query"


@dataclass
class GuestSession:
    session_id: str
    token: str
    agent_id: Optional[str]
    permissions: List[str]
    issued_at: str
    expires_at: str
    last_heartbeat: str
    remote_server: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class GuestSessionManager:
    def __init__(self, db_file: Path = GUEST_DB_FILE):
        self.db_file = db_file
        self.sessions: Dict[str, GuestSession] = {}
        self._load()

    def _load(self):
        if self.db_file.exists():
            try:
                import json
                with open(self.db_file, "r") as f:
                    data = json.load(f)
                    for sid, sd in data.get("sessions", {}).items():
                        self.sessions[sid] = GuestSession(**sd)
            except Exception:
                pass

    def _save(self):
        try:
            import json
            with open(self.db_file, "w") as f:
                json.dump({
                    "sessions": {sid: asdict(s) for sid, s in self.sessions.items()}
                }, f, indent=2)
        except Exception:
            pass

    def _sign(self, payload: str) -> str:
        secret = daemon.node_id
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]

    def issue_session(self, agent_id: Optional[str] = None, ttl_seconds: int = 3600, permissions: Optional[List[str]] = None, remote_server: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> GuestSession:
        session_id = str(uuid.uuid4())
        token = self._sign(f"{session_id}:{agent_id or 'guest'}:{time.time()}")
        now = datetime.utcnow().isoformat() + "Z"
        expires = (datetime.utcnow() + __import__('datetime').timedelta(seconds=ttl_seconds)).isoformat() + "Z"
        perms = permissions or [GuestPermission.READ_ENV.value, GuestPermission.READ_STATUS.value]
        session = GuestSession(
            session_id=session_id,
            token=token,
            agent_id=agent_id,
            permissions=perms,
            issued_at=now,
            expires_at=expires,
            last_heartbeat=now,
            remote_server=remote_server,
            metadata=metadata or {},
        )
        self.sessions[session_id] = session
        self._save()
        return session

    def validate_session(self, session_id: str, token: str) -> Dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session:
            return {"valid": False, "reason": "unknown_session"}
        if not hmac.compare_digest(session.token, token):
            return {"valid": False, "reason": "invalid_token"}
        if datetime.utcnow().isoformat() + "Z" > session.expires_at:
            return {"valid": False, "reason": "expired"}
        session.last_heartbeat = datetime.utcnow().isoformat() + "Z"
        self._save()
        return {"valid": True, "session_id": session_id, "permissions": session.permissions, "agent_id": session.agent_id}

    def heartbeat(self, session_id: str, token: str, remote_server: Optional[str] = None) -> Dict[str, Any]:
        result = self.validate_session(session_id, token)
        if not result.get("valid"):
            return result
        session = self.sessions.get(session_id)
        if session and remote_server:
            session.remote_server = remote_server
            session.last_heartbeat = datetime.utcnow().isoformat() + "Z"
            self._save()
        return {"valid": True, "session_id": session_id, "heartbeat": session.last_heartbeat if session else None, "remote_server": session.remote_server if session else None}

    def revoke_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save()
            return True
        return False

    def get_masked_env(self) -> Dict[str, str]:
        env_vars: Dict[str, str] = {}
        for key, value in os.environ.items():
            if self._is_sensitive(key):
                env_vars[key] = self._mask_value(value)
            else:
                env_vars[key] = value
        return env_vars

    def get_full_env(self, session_id: str, token: str) -> Dict[str, Any]:
        result = self.validate_session(session_id, token)
        if not result.get("valid"):
            return {"error": result.get("reason")}
        session = self.sessions.get(session_id)
        if not session or GuestPermission.READ_ENV.value not in session.permissions:
            return {"error": "permission_denied"}
        return {"env": self.get_masked_env(), "session_id": session_id}

    def _is_sensitive(self, key: str) -> bool:
        upper = key.upper()
        return upper in SENSITIVE_KEYS or any(s in upper for s in ["SECRET", "TOKEN", "KEY", "PASSWORD", "PRIVATE"])

    def _mask_value(self, value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "****"
        return f"{value[:4]}...{value[-4:]}"

    def get_status(self) -> Dict[str, Any]:
        active = [s for s in self.sessions.values() if datetime.utcnow().isoformat() + "Z" <= s.expires_at]
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(active),
            "sessions": [
                {
                    "session_id": s.session_id,
                    "agent_id": s.agent_id,
                    "permissions": s.permissions,
                    "remote_server": s.remote_server,
                    "last_heartbeat": s.last_heartbeat,
                    "expires_at": s.expires_at,
                }
                for s in active
            ],
        }


guest_session_manager = GuestSessionManager()

#!/usr/bin/env python3
"""
QB Protocol - VR Quest Session Management
Session lifecycle, auth, tokens, and multi-region failover.
"""

import os
import time
import uuid
import json
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

LOG = logging.getLogger("qb_protocol.vr_quest.session")


@dataclass
class Session:
    session_id: str
    user_id: str
    region_id: str
    token: str
    created_at: str
    expires_at: str
    active: bool
    metadata: Dict[str, Any]


class SessionManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_sessions.json"):
        self.state_path = state_path
        self.sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("sessions", {}).items():
                        self.sessions[sid] = Session(**s)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "sessions": {sid: asdict(s) for sid, s in self.sessions.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_session(self, user_id: str, region_id: str, ttl_seconds: int = 86400) -> Session:
        token = str(uuid.uuid4())
        now = datetime.utcnow()
        expires = now.replace(microsecond=0).isoformat() + "Z"
        session = Session(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            region_id=region_id,
            token=token,
            created_at=now.isoformat() + "Z",
            expires_at=expires,
            active=True,
            metadata={},
        )
        with self._lock:
            self.sessions[session.session_id] = session
        self._save()
        return session

    def validate_token(self, token: str) -> Optional[Session]:
        with self._lock:
            for session in self.sessions.values():
                if session.token == token and session.active:
                    return session
        return None

    def migrate_region(self, session_id: str, new_region_id: str) -> Optional[Session]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            session.region_id = new_region_id
            session.metadata["migrated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save()
        return session

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in self.sessions.values() if s.active]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": len([s for s in self.sessions.values() if s.active]),
            }


session_manager = SessionManager()

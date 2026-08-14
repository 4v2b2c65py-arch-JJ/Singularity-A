#!/usr/bin/env python3
"""
QB Protocol - WebRTC Voice Manager
Voice call management with WebRTC and signaling.
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

LOG = logging.getLogger("qb_protocol.telecom.voice")


@dataclass
class WebRTCSession:
    session_id: str
    caller_id: str
    callee_id: str
    status: str
    turn_url: Optional[str]
    turn_username: Optional[str]
    turn_password: Optional[str]
    metadata: Dict[str, Any]
    created_at: str


class WebRTCManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_telecom_webrtc.json"):
        self.state_path = state_path
        self.sessions: Dict[str, WebRTCSession] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("sessions", {}).items():
                        self.sessions[sid] = WebRTCSession(**s)
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

    def create_session(self, caller_id: str, callee_id: str, turn_config: Optional[Dict[str, str]] = None) -> WebRTCSession:
        session = WebRTCSession(
            session_id=str(uuid.uuid4()),
            caller_id=caller_id,
            callee_id=callee_id,
            status="ringing",
            turn_url=turn_config.get("url") if turn_config else None,
            turn_username=turn_config.get("username") if turn_config else None,
            turn_password=turn_config.get("password") if turn_config else None,
            metadata={},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.sessions[session.session_id] = session
        self._save()
        return session

    def update_session_status(self, session_id: str, status: str) -> Optional[WebRTCSession]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            session.status = status
        self._save()
        return session

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self.sessions.get(session_id)
            return asdict(session) if session else None

    def get_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in self.sessions.values()]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            active = len([s for s in self.sessions.values() if s.status in ["ringing", "connected"]])
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": active,
            }


webrtc_manager = WebRTCManager()

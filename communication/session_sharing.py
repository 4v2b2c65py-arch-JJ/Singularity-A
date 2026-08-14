#!/usr/bin/env python3
"""
QB Protocol - Session Sharing
Shared session and data transfer management.
"""

import os
import time
import uuid
import json
import logging
import threading
import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.session_sharing")


class SessionStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    TRANSFERRING = "transferring"


class TransferStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CLEARED = "cleared"


@dataclass
class DataTransfer:
    transfer_id: str
    session_id: str
    from_participant: str
    to_participant: str
    data_type: str
    size_bytes: int
    status: str
    start_time: str
    end_time: Optional[str]
    checksum: str
    metadata: Dict[str, Any]


@dataclass
class SharedSession:
    session_id: str
    host: str
    participants: List[str]
    status: str
    created_at: str
    updated_at: str
    memory_allocated: int
    memory_used: int
    data_transfers: List[str]
    metadata: Dict[str, Any]


@dataclass
class ServerClearance:
    clearance_id: str
    session_id: str
    participant_id: str
    data_cleared: bool
    memory_cleared: bool
    timestamp: str
    metadata: Dict[str, Any]


class SessionSharing:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent / "qb_protocol_sessions.json"):
        self.state_path = state_path
        self.sessions: Dict[str, SharedSession] = {}
        self.transfers: Dict[str, DataTransfer] = {}
        self.clearances: Dict[str, ServerClearance] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("sessions", {}).items():
                        self.sessions[sid] = SharedSession(**s)
                    for tid, t in data.get("transfers", {}).items():
                        self.transfers[tid] = DataTransfer(**t)
                    for cid, c in data.get("clearances", {}).items():
                        self.clearances[cid] = ServerClearance(**c)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "sessions": {sid: asdict(s) for sid, s in self.sessions.items()},
                    "transfers": {tid: asdict(t) for tid, t in self.transfers.items()},
                    "clearances": {cid: asdict(c) for cid, c in self.clearances.items()},
                }, f, indent=2, default=str)
        except Exception:
            pass

    def create_session(self, host: str, participants: List[str], metadata: Optional[Dict[str, Any]] = None) -> SharedSession:
        session = SharedSession(
            session_id=str(uuid.uuid4()),
            host=host,
            participants=participants,
            status=SessionStatus.ACTIVE.value,
            created_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
            memory_allocated=0,
            memory_used=0,
            data_transfers=[],
            metadata=metadata or {},
        )
        with self._lock:
            self.sessions[session.session_id] = session
        self._save()
        return session

    def join_session(self, session_id: str, participant_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "error", "message": "Session not found"}
            if participant_id not in session.participants:
                session.participants.append(participant_id)
                session.updated_at = datetime.utcnow().isoformat() + "Z"
            self._save()
            return {"status": "success", "message": f"Joined session {session_id}", "participants": session.participants}

    def leave_session(self, session_id: str, participant_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"status": "error", "message": "Session not found"}
            if participant_id in session.participants:
                session.participants.remove(participant_id)
                session.updated_at = datetime.utcnow().isoformat() + "Z"
            self._save()
            return {"status": "success", "message": f"Left session {session_id}", "participants": session.participants}

    def transfer_data(self, session_id: str, from_participant: str, to_participant: str, data: bytes, data_type: str = "binary") -> DataTransfer:
        checksum = hashlib.sha256(data).hexdigest()
        transfer = DataTransfer(
            transfer_id=str(uuid.uuid4()),
            session_id=session_id,
            from_participant=from_participant,
            to_participant=to_participant,
            data_type=data_type,
            size_bytes=len(data),
            status=TransferStatus.IN_PROGRESS.value,
            start_time=datetime.utcnow().isoformat() + "Z",
            end_time=None,
            checksum=checksum,
            metadata={"encoding": "base64"},
        )
        with self._lock:
            self.transfers[transfer.transfer_id] = transfer
            session = self.sessions.get(session_id)
            if session:
                session.data_transfers.append(transfer.transfer_id)
                session.memory_used += len(data)
                session.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return transfer

    def complete_transfer(self, transfer_id: str) -> Dict[str, Any]:
        with self._lock:
            transfer = self.transfers.get(transfer_id)
            if not transfer:
                return {"status": "error", "message": "Transfer not found"}
            transfer.status = TransferStatus.COMPLETED.value
            transfer.end_time = datetime.utcnow().isoformat() + "Z"
            self._save()
            return {"status": "success", "message": "Transfer completed", "transfer": asdict(transfer)}

    def clear_server_data(self, session_id: str, participant_id: str, clear_memory: bool = True) -> ServerClearance:
        clearance = ServerClearance(
            clearance_id=str(uuid.uuid4()),
            session_id=session_id,
            participant_id=participant_id,
            data_cleared=True,
            memory_cleared=clear_memory,
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={},
        )
        with self._lock:
            self.clearances[clearance.clearance_id] = clearance
            session = self.sessions.get(session_id)
            if session:
                if clear_memory:
                    session.memory_used = 0
                session.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save()
        return clearance

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self.sessions.get(session_id)
            return asdict(session) if session else None

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(s) for s in self.sessions.values() if s.status == SessionStatus.ACTIVE.value]

    def get_transfers(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            transfers = list(self.transfers.values())
            if session_id:
                transfers = [t for t in transfers if t.session_id == session_id]
            return [asdict(t) for t in transfers]

    def get_clearances(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            clearances = list(self.clearances.values())
            if session_id:
                clearances = [c for c in clearances if c.session_id == session_id]
            return [asdict(c) for c in clearances]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": len([s for s in self.sessions.values() if s.status == SessionStatus.ACTIVE.value]),
                "total_transfers": len(self.transfers),
                "completed_transfers": len([t for t in self.transfers.values() if t.status == TransferStatus.COMPLETED.value]),
                "total_clearances": len(self.clearances),
            }


session_sharing = SessionSharing()

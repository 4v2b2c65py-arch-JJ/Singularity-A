#!/usr/bin/env python3
"""
QB Protocol - VR Warp Barrier Manager
Barrier blockage and reality permit compliance.
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

LOG = logging.getLogger("qb_protocol.vr_quest.warp.barrier")


@dataclass
class RealityPermit:
    permit_id: str
    realm_id: str
    requester_id: str
    valid: bool
    expires_at: str
    conditions: List[str]
    metadata: Dict[str, Any]
    created_at: str


class BarrierManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "qb_protocol_vr_barrier.json"):
        self.state_path = state_path
        self.permits: Dict[str, RealityPermit] = {}
        self.barriers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for pid, p in data.get("permits", {}).items():
                        self.permits[pid] = RealityPermit(**p)
                    self.barriers = data.get("barriers", {})
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "permits": {pid: asdict(p) for pid, p in self.permits.items()},
                    "barriers": self.barriers,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_barrier(self, realm_id: str, barrier_type: str, strength: float = 1.0, conditions: Optional[List[str]] = None) -> Dict[str, Any]:
        barrier = {
            "barrier_id": str(uuid.uuid4()),
            "realm_id": realm_id,
            "barrier_type": barrier_type,
            "strength": strength,
            "conditions": conditions or [],
            "active": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        with self._lock:
            self.barriers[barrier["barrier_id"]] = barrier
        self._save()
        return barrier

    def issue_permit(self, realm_id: str, requester_id: str, ttl_seconds: int = 3600, conditions: Optional[List[str]] = None) -> RealityPermit:
        now = datetime.utcnow()
        expires = now.replace(microsecond=0).isoformat() + "Z"
        permit = RealityPermit(
            permit_id=str(uuid.uuid4()),
            realm_id=realm_id,
            requester_id=requester_id,
            valid=True,
            expires_at=expires,
            conditions=conditions or [],
            metadata={"ttl_seconds": ttl_seconds},
            created_at=now.isoformat() + "Z",
        )
        with self._lock:
            self.permits[permit.permit_id] = permit
        self._save()
        return permit

    def validate_permit(self, permit_id: str, realm_id: str) -> bool:
        with self._lock:
            permit = self.permits.get(permit_id)
            if not permit or not permit.valid:
                return False
            if permit.realm_id != realm_id:
                return False
            return True

    def get_permits(self, realm_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            permits = list(self.permits.values())
            if realm_id:
                permits = [p for p in permits if p.realm_id == realm_id]
            return [asdict(p) for p in permits]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_barriers": len(self.barriers),
                "total_permits": len(self.permits),
                "active_permits": len([p for p in self.permits.values() if p.valid]),
            }


barrier_manager = BarrierManager()

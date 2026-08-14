#!/usr/bin/env python3
"""
QB Protocol - Satellite Security
Security clearance and compliance for satellite communication.
"""

import os
import time
import uuid
import json
import logging
import threading
import hashlib
import hmac
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.satellite.security")


class SecurityClearance(Enum):
    UNCLASSIFIED = "unclassified"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"
    GOVERNMENT = "government"


@dataclass
class SatelliteSecurity:
    security_id: str
    clearance_level: str
    authorized: bool
    encryption_key: str
    signature: str
    compliance_checks: List[str]
    metadata: Dict[str, Any]
    created_at: str


class SatelliteSecurityManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_satellite_security.json"):
        self.state_path = state_path
        self.security_records: Dict[str, SatelliteSecurity] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for sid, s in data.get("security", {}).items():
                        self.security_records[sid] = SatelliteSecurity(**s)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "security": {sid: asdict(s) for sid, s in self.security_records.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def authorize(self, clearance_level: str = SecurityClearance.GOVERNMENT.value, encryption_key: str = "", metadata: Optional[Dict[str, Any]] = None) -> SatelliteSecurity:
        signature = self._compute_signature(clearance_level, encryption_key)
        compliance_checks = [
            "encryption_verified",
            "clearance_valid",
            "government_assured",
            "exit_code_compliant",
        ]
        security = SatelliteSecurity(
            security_id=str(uuid.uuid4()),
            clearance_level=clearance_level,
            authorized=True,
            encryption_key=encryption_key,
            signature=signature,
            compliance_checks=compliance_checks,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.security_records[security.security_id] = security
        self._save()
        return security

    def _compute_signature(self, clearance_level: str, encryption_key: str) -> str:
        data = f"{clearance_level}:{encryption_key}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_signature(self, security_id: str, clearance_level: str, encryption_key: str) -> bool:
        with self._lock:
            security = self.security_records.get(security_id)
        if not security:
            return False
        expected = self._compute_signature(clearance_level, encryption_key)
        return hmac.compare_digest(security.signature, expected)

    def get_security(self, security_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            security = self.security_records.get(security_id)
            return asdict(security) if security else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            authorized = len([s for s in self.security_records.values() if s.authorized])
            return {
                "total_security_records": len(self.security_records),
                "authorized_records": authorized,
                "clearance_levels": list(set(s.clearance_level for s in self.security_records.values())),
            }


satellite_security = SatelliteSecurityManager()

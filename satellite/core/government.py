#!/usr/bin/env python3
"""
QB Protocol - Government Assurance
Government compliance and assurance for satellite communication.
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
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.satellite.government")


class ComplianceLevel(Enum):
    BASIC = "basic"
    GOVERNMENT = "government"
    MILITARY = "military"
    ASSURED = "assured"


@dataclass
class GovernmentAssurance:
    assurance_id: str
    compliance_level: str
    approved: bool
    authority: str
    certification_id: str
    audit_trail: List[str]
    restrictions: List[str]
    metadata: Dict[str, Any]
    created_at: str


class GovernmentAssuranceManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_satellite_government.json"):
        self.state_path = state_path
        self.assurances: Dict[str, GovernmentAssurance] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for aid, a in data.get("assurances", {}).items():
                        self.assurances[aid] = GovernmentAssurance(**a)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "assurances": {aid: asdict(a) for aid, a in self.assurances.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def approve(self, compliance_level: str = ComplianceLevel.GOVERNMENT.value, authority: str = "QB Protocol", certification_id: str = "", restrictions: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> GovernmentAssurance:
        assurance = GovernmentAssurance(
            assurance_id=str(uuid.uuid4()),
            compliance_level=compliance_level,
            approved=True,
            authority=authority,
            certification_id=certification_id or str(uuid.uuid4()),
            audit_trail=[datetime.utcnow().isoformat() + "Z"],
            restrictions=restrictions or ["no_simulation_fallback", "real_modem_required", "government_audit"],
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.assurances[assurance.assurance_id] = assurance
        self._save()
        return assurance

    def revoke(self, assurance_id: str) -> bool:
        with self._lock:
            assurance = self.assurances.get(assurance_id)
            if not assurance:
                return False
            assurance.approved = False
            assurance.audit_trail.append(datetime.utcnow().isoformat() + "Z: revoked")
        self._save()
        return True

    def get_assurance(self, assurance_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            assurance = self.assurances.get(assurance_id)
            return asdict(assurance) if assurance else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            approved = len([a for a in self.assurances.values() if a.approved])
            return {
                "total_assurances": len(self.assurances),
                "approved_assurances": approved,
                "compliance_levels": list(set(a.compliance_level for a in self.assurances.values())),
            }


government_assurance = GovernmentAssuranceManager()

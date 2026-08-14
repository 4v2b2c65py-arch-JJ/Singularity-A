#!/usr/bin/env python3
"""
QB Protocol - VR Warp Security Checker
Security checks for barrier and reality permit compliance.
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

LOG = logging.getLogger("qb_protocol.vr_quest.warp.security")


@dataclass
class SecurityCheck:
    check_id: str
    warp_id: str
    check_type: str
    status: str
    details: Dict[str, Any]
    metadata: Dict[str, Any]
    checked_at: str


class SecurityChecker:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent.parent / "qb_protocol_vr_security.json"):
        self.state_path = state_path
        self.checks: List[SecurityCheck] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.checks = [SecurityCheck(**c) for c in data.get("checks", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "checks": [asdict(c) for c in self.checks[-1000:]]
                }, f, indent=2, default=str)
        except Exception:
            pass

    def run_security_check(self, warp_id: str, check_type: str, details: Dict[str, Any]) -> SecurityCheck:
        status = "passed"
        for key, value in details.items():
            if value < 0 or value > 1:
                status = "failed"
                break

        check = SecurityCheck(
            check_id=str(uuid.uuid4()),
            warp_id=warp_id,
            check_type=check_type,
            status=status,
            details=details,
            metadata={"auto": True},
            checked_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.checks.append(check)
            if len(self.checks) > 1000:
                self.checks = self.checks[-1000:]
        self._save()
        return check

    def get_checks(self, warp_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            checks = self.checks
            if warp_id:
                checks = [c for c in checks if c.warp_id == warp_id]
            return [asdict(c) for c in checks[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            recent = self.checks[-10:]
            passed = len([c for c in recent if c.status == "passed"])
            return {
                "total_checks": len(self.checks),
                "recent_pass_rate": round(passed / len(recent), 2) if recent else 0,
            }


security_checker = SecurityChecker()

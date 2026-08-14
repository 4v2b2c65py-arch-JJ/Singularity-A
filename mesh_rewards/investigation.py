#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Investigation Agent
Private mode deep-dive into user data for eligibility and fraud detection.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

LOG = logging.getLogger("qb_protocol.mesh_rewards.investigation")


@dataclass
class InvestigationCase:
    case_id: str
    device_id: str
    trigger: str
    status: str
    score: float
    eligible: bool
    evidence: Dict[str, Any]
    started_at: str
    resolved_at: Optional[str]


class InvestigationAgent:
    """Private investigation agent for mesh reward eligibility."""

    def __init__(self):
        self.cases: Dict[str, InvestigationCase] = {}
        self._lock = threading.Lock()
        self._running = False

    def start_investigation(self, device_id: str, trigger: str, evidence: Dict[str, Any] = None) -> InvestigationCase:
        case_id = str(uuid.uuid4())
        case = InvestigationCase(
            case_id=case_id,
            device_id=device_id,
            trigger=trigger,
            status="investigating",
            score=0.0,
            eligible=False,
            evidence=evidence or {},
            started_at=datetime.utcnow().isoformat() + "Z",
            resolved_at=None,
        )
        with self._lock:
            self.cases[case_id] = case
        LOG.info("Investigation started: %s for %s", case_id, device_id)
        return case

    def evaluate_eligibility(self, case_id: str) -> Dict[str, Any]:
        with self._lock:
            case = self.cases.get(case_id)
        if not case:
            return {"error": "case_not_found"}

        try:
            score = self._calculate_trust_score(case)
            eligible = score >= 0.6
            with self._lock:
                case.status = "resolved"
                case.score = score
                case.eligible = eligible
                case.resolved_at = datetime.utcnow().isoformat() + "Z"
            LOG.info("Investigation resolved: %s eligible=%s score=%.2f", case_id, eligible, score)
            return {
                "case_id": case_id,
                "device_id": case.device_id,
                "eligible": eligible,
                "score": score,
                "status": case.status,
            }
        except Exception as exc:
            LOG.warning("Investigation failed: %s", exc)
            return {"error": str(exc), "case_id": case_id}

    def _calculate_trust_score(self, case: InvestigationCase) -> float:
        evidence = case.evidence or {}
        score = 0.5
        if evidence.get("mesh_uptime", 0) > 3600:
            score += 0.1
        if evidence.get("valid_contributions", 0) > 10:
            score += 0.1
        if evidence.get("icloud_verified"):
            score += 0.1
        if evidence.get("secure_enclave"):
            score += 0.1
        if evidence.get("suspicious_activity"):
            score -= 0.3
        if evidence.get("failed_verifications", 0) > 3:
            score -= 0.2
        return max(0.0, min(1.0, score))

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            case = self.cases.get(case_id)
            return asdict(case) if case else None

    def get_cases(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            cases = list(self.cases.values())
        if device_id:
            cases = [c for c in cases if c.device_id == device_id]
        return [asdict(c) for c in cases]


investigation_agent = InvestigationAgent()

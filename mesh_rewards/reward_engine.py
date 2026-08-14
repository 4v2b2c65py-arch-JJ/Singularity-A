#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Reward Engine
AI model-controlled reward distribution with investigation, trial, and on-chain distribution.
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

LOG = logging.getLogger("qb_protocol.mesh_rewards.reward_engine")

CONTRIBUTION_WEIGHTS = {
    "compute": 1.0,
    "storage": 0.5,
    "bandwidth": 0.8,
    "ai_inference": 2.0,
    "mesh_relay": 1.5,
    "brain_reading": 1.2,
    "voice": 0.9,
    "image": 1.1,
}


@dataclass
class Contribution:
    contribution_id: str
    device_id: str
    contribution_type: str
    weight: float
    duration_seconds: float
    data_amount: float
    timestamp: str
    cloud_space_bytes: int = 0


@dataclass
class RewardPayout:
    payout_id: str
    device_id: str
    contribution_score: float
    credit_amount: float
    sats_amount: int
    token_type: str
    status: str
    trial_passed: bool
    distributed: bool
    timestamp: str


class RewardEngine:
    """AI model-controlled reward engine with investigation and on-chain distribution."""

    def __init__(self):
        self.contributions: List[Contribution] = []
        self.payouts: List[RewardPayout] = []
        self._lock = threading.Lock()
        self._pending_trials: Dict[str, RewardPayout] = {}

    def record_contribution(self, device_id: str, contribution_type: str, duration_seconds: float = 0.0, data_amount: float = 0.0, cloud_space_bytes: int = 0) -> Contribution:
        weight = CONTRIBUTION_WEIGHTS.get(contribution_type, 1.0)
        contribution = Contribution(
            contribution_id=str(uuid.uuid4()),
            device_id=device_id,
            contribution_type=contribution_type,
            weight=weight,
            duration_seconds=duration_seconds,
            data_amount=data_amount,
            cloud_space_bytes=cloud_space_bytes,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.contributions.append(contribution)
        LOG.info("Contribution recorded: %s (%s)", device_id, contribution_type)
        return contribution

    def calculate_device_score(self, device_id: str, window_seconds: float = 3600.0) -> float:
        cutoff = time.time() - window_seconds
        score = 0.0
        with self._lock:
            for c in self.contributions:
                if c.device_id == device_id:
                    ts = datetime.fromisoformat(c.timestamp.replace("Z", "+00:00")).timestamp()
                    if ts >= cutoff:
                        score += c.weight * max(c.duration_seconds, 1.0) * (1.0 + c.data_amount / 1024.0)
        return score

    def initiate_reward_trial(self, device_id: str, contribution_score: float, evidence: Dict[str, Any] = None) -> RewardPayout:
        payout = RewardPayout(
            payout_id=str(uuid.uuid4()),
            device_id=device_id,
            contribution_score=contribution_score,
            credit_amount=contribution_score * 10.0,
            sats_amount=0,
            token_type="credit",
            status="trial",
            trial_passed=False,
            distributed=False,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self._pending_trials[payout.payout_id] = payout
        LOG.info("Reward trial initiated: %s score=%.2f", device_id, contribution_score)
        return payout

    def resolve_trial(self, payout_id: str, approved: bool, failure_reason: str = "") -> Optional[RewardPayout]:
        with self._lock:
            payout = self._pending_trials.get(payout_id)
        if not payout:
            return None

        if approved:
            from mesh_rewards.blockchain_rates import blockchain_rates
            sats = blockchain_rates.convert_credits_to_sats(payout.credit_amount)
            payout.sats_amount = sats
            payout.status = "approved"
            payout.trial_passed = True
            payout.distributed = False
        else:
            payout.status = "rejected"
            payout.trial_passed = False

        with self._lock:
            self.payouts.append(payout)
            self._pending_trials.pop(payout_id, None)
        LOG.info("Trial resolved: %s approved=%s", payout_id, approved)
        return payout

    def distribute_reward(self, payout_id: str, recipient_devices: List[str] = None) -> bool:
        with self._lock:
            payout = next((p for p in self.payouts if p.payout_id == payout_id), None)
        if not payout or not payout.trial_passed:
            return False
        payout.distributed = True
        payout.status = "distributed"
        LOG.info("Reward distributed: %s sats=%d", payout_id, payout.sats_amount)
        return True

    def get_leaderboard(self, window_seconds: float = 86400.0) -> List[Dict[str, Any]]:
        cutoff = time.time() - window_seconds
        scores: Dict[str, float] = {}
        with self._lock:
            for c in self.contributions:
                ts = datetime.fromisoformat(c.timestamp.replace("Z", "+00:00")).timestamp()
                if ts >= cutoff:
                    scores[c.device_id] = scores.get(c.device_id, 0.0) + c.weight * max(c.duration_seconds, 1.0) * (1.0 + c.data_amount / 1024.0)
        return [{"device_id": k, "score": v} for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_contributions": len(self.contributions),
                "total_payouts": len(self.payouts),
                "pending_trials": len(self._pending_trials),
            }


reward_engine = RewardEngine()

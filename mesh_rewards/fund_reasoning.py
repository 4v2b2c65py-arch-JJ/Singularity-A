#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Fund Reasoning
Agent reasoning for fund requirements based on data metrics across celestial nodes.
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

LOG = logging.getLogger("qb_protocol.mesh_rewards.fund_reasoning")


@dataclass
class FundRequest:
    request_id: str
    device_id: str
    user_id: str
    amount_requested: float
    reason: str
    metrics: Dict[str, Any]
    celestial_nodes_consulted: List[str]
    approved: bool
    approved_amount: float
    reasoning: str
    timestamp: str


class FundReasoningAgent:
    """Agent that reasons about fund requirements using celestial node data."""

    def __init__(self):
        self.requests: Dict[str, FundRequest] = {}
        self._lock = threading.Lock()

    def evaluate_fund_request(self, device_id: str, user_id: str, amount_requested: float, reason: str, metrics: Dict[str, Any] = None) -> FundRequest:
        request_id = str(uuid.uuid4())
        metrics = metrics or {}
        celestial_nodes_consulted = []
        
        try:
            from qb_protocol.mesh_rewards.celestial_nodes import celestial_node_manager
            nodes = celestial_node_manager.get_nodes_by_user(user_id)
            for node in nodes:
                celestial_nodes_consulted.append(node["node_id"])
                celestial_node_manager.update_contribution(node["node_id"], 0.1)
        except Exception as exc:
            LOG.warning("Celestial node consultation failed: %s", exc)

        approved = False
        approved_amount = 0.0
        reasoning = ""
        
        try:
            from qb_protocol.mesh_rewards.wallet import reward_wallet
            balance = reward_wallet.get_balance(device_id)
            current_credits = balance.get("credits", 0.0) if balance else 0.0
            
            mesh_uptime = metrics.get("mesh_uptime", 0)
            contribution_score = metrics.get("contribution_score", 0)
            valid_contributions = metrics.get("valid_contributions", 0)
            cloud_space = metrics.get("cloud_space_bytes", 0)
            
            if current_credits >= amount_requested:
                approved = True
                approved_amount = amount_requested
                reasoning = "Sufficient balance available."
            elif contribution_score > 50 and valid_contributions > 20 and mesh_uptime > 3600:
                approved = True
                approved_amount = min(amount_requested, contribution_score * 0.1)
                reasoning = f"Approved based on high contribution score ({contribution_score:.1f}) and valid contributions ({valid_contributions})."
            elif celestial_nodes_consulted:
                approved = True
                approved_amount = min(amount_requested, 10.0)
                reasoning = f"Approved based on celestial node assistance ({len(celestial_nodes_consulted)} nodes)."
            else:
                reasoning = "Insufficient metrics for approval."
        except Exception as exc:
            LOG.warning("Fund reasoning failed: %s", exc)
            reasoning = f"Error during evaluation: {str(exc)}"

        request = FundRequest(
            request_id=request_id,
            device_id=device_id,
            user_id=user_id,
            amount_requested=amount_requested,
            reason=reason,
            metrics=metrics,
            celestial_nodes_consulted=celestial_nodes_consulted,
            approved=approved,
            approved_amount=approved_amount,
            reasoning=reasoning,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.requests[request_id] = request
        LOG.info("Fund request evaluated: %s approved=%s amount=%.2f", request_id, approved, approved_amount)
        return request

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            request = self.requests.get(request_id)
            return asdict(request) if request else None

    def get_requests(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            requests = list(self.requests.values())
        if user_id:
            requests = [r for r in requests if r.user_id == user_id]
        return [asdict(r) for r in requests]


fund_reasoning_agent = FundReasoningAgent()

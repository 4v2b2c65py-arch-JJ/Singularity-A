#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Celestial Nodes
Multi-verse celestial node matching across timelines, planes, realms, and environments.
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

LOG = logging.getLogger("qb_protocol.mesh_rewards.celestial")

ENVIRONMENT_TYPES = ["timeline", "plane", "realm", "environment", "dimension", "void"]


@dataclass
class CelestialNode:
    node_id: str
    user_id: str
    environment_type: str
    environment_id: str
    device_id: str
    btc_public_address: str
    sats_rank: int
    contribution_score: float
    linked_nodes: List[str]
    metadata: Dict[str, Any]
    created_at: str
    last_seen: str


class CelestialNodeManager:
    """Manages celestial nodes across multi-verse environments."""

    def __init__(self):
        self.nodes: Dict[str, CelestialNode] = {}
        self._lock = threading.Lock()
        self._rankings: Dict[str, List[Dict[str, Any]]] = {env: [] for env in ENVIRONMENT_TYPES}

    def register_node(self, user_id: str, environment_type: str, environment_id: str, device_id: str, btc_public_address: str, metadata: Dict[str, Any] = None) -> CelestialNode:
        node_id = str(uuid.uuid4())
        node = CelestialNode(
            node_id=node_id,
            user_id=user_id,
            environment_type=environment_type,
            environment_id=environment_id,
            device_id=device_id,
            btc_public_address=btc_public_address,
            sats_rank=0,
            contribution_score=0.0,
            linked_nodes=[],
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat() + "Z",
            last_seen=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.nodes[node_id] = node
        LOG.info("Celestial node registered: %s (%s/%s)", node_id, environment_type, environment_id)
        return node

    def link_nodes(self, node_a: str, node_b: str):
        with self._lock:
            if node_a in self.nodes and node_b in self.nodes:
                if node_b not in self.nodes[node_a].linked_nodes:
                    self.nodes[node_a].linked_nodes.append(node_b)
                if node_a not in self.nodes[node_b].linked_nodes:
                    self.nodes[node_b].linked_nodes.append(node_a)
                LOG.info("Linked nodes: %s <-> %s", node_a, node_b)

    def update_contribution(self, node_id: str, score: float):
        with self._lock:
            if node_id in self.nodes:
                self.nodes[node_id].contribution_score += score
                self.nodes[node_id].last_seen = datetime.utcnow().isoformat() + "Z"

    def get_nodes_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(n) for n in self.nodes.values() if n.user_id == user_id]

    def get_nodes_by_environment(self, environment_type: str, environment_id: str = "") -> List[Dict[str, Any]]:
        with self._lock:
            nodes = []
            for n in self.nodes.values():
                if n.environment_type == environment_type:
                    if not environment_id or n.environment_id == environment_id:
                        nodes.append(asdict(n))
            return nodes

    def get_linked_nodes(self, node_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            node = self.nodes.get(node_id)
            if not node:
                return []
            return [asdict(self.nodes[nid]) for nid in node.linked_nodes if nid in self.nodes]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_nodes": len(self.nodes),
                "environments": {env: len([n for n in self.nodes.values() if n.environment_type == env]) for env in ENVIRONMENT_TYPES},
            }


celestial_node_manager = CelestialNodeManager()

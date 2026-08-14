#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Multiverse Ranker
Ranks BTC public addresses across timelines, planes, realms, and environments.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

LOG = logging.getLogger("qb_protocol.mesh_rewards.ranker")

RANKER_STATE_PATH = Path.home() / ".qb_protocol_multiverse_ranker.json"


@dataclass
class RankedAddress:
    address: str
    user_id: str
    node_id: str
    environment_type: str
    environment_id: str
    sats: int
    btc_value_usd: float
    rank: int
    verified: bool
    timestamp: str


class MultiverseRanker:
    """Ranks BTC public addresses across multi-verse environments."""

    def __init__(self, state_path: Path = RANKER_STATE_PATH):
        self.state_path = state_path
        self.rankings: Dict[str, List[RankedAddress]] = {env: [] for env in ["timeline", "plane", "realm", "environment", "dimension", "void", "global"]}
        self._lock = threading.Lock()
        self._btc_usd = 50000.0
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                for env, entries in data.get("rankings", {}).items():
                    self.rankings[env] = [RankedAddress(**e) for e in entries]
                self._btc_usd = float(data.get("btc_usd", 50000.0))
            except Exception as exc:
                LOG.warning("Failed to load ranker state: %s", exc)

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "rankings": {k: [asdict(r) for r in v] for k, v in self.rankings.items()},
                    "btc_usd": self._btc_usd,
                }, f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save ranker state: %s", exc)

    def update_btc_price(self, btc_usd: float):
        with self._lock:
            self._btc_usd = btc_usd
            self._save()

    def submit_address(self, address: str, user_id: str, node_id: str, environment_type: str, environment_id: str, sats: int, verified: bool = False) -> RankedAddress:
        btc_value_usd = (sats / 100000000.0) * self._btc_usd
        ranked = RankedAddress(
            address=address,
            user_id=user_id,
            node_id=node_id,
            environment_type=environment_type,
            environment_id=environment_id,
            sats=sats,
            btc_value_usd=btc_value_usd,
            rank=0,
            verified=verified,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            env = environment_type if environment_type in self.rankings else "global"
            self.rankings[env].append(ranked)
            self.rankings[env].sort(key=lambda r: r.sats, reverse=True)
            for idx, r in enumerate(self.rankings[env]):
                r.rank = idx + 1
            self._save()
        LOG.info("Address submitted: %s sats=%d env=%s/%s rank=%d", address, sats, environment_type, environment_id, ranked.rank)
        return ranked

    def get_leaderboard(self, environment_type: str = "global", limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            env = environment_type if environment_type in self.rankings else "global"
            entries = self.rankings[env][:limit]
            return [asdict(r) for r in entries]

    def get_user_rank(self, user_id: str, environment_type: str = "global") -> Optional[Dict[str, Any]]:
        with self._lock:
            env = environment_type if environment_type in self.rankings else "global"
            for r in self.rankings[env]:
                if r.user_id == user_id:
                    return asdict(r)
        return None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "btc_usd": self._btc_usd,
                "total_addresses": sum(len(v) for v in self.rankings.values()),
                "environments": {k: len(v) for k, v in self.rankings.items()},
            }


multiverse_ranker = MultiverseRanker()

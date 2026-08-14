#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Multiverse Ranker
Authoritative rankings sourced from the Tablet of Destinies oracle.
The universal data structure is set from beyond the veil of our code mirror.
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

LOG = logging.getLogger("qb_protocol.mesh_reards.ranker")

RANKER_STATE_PATH = Path.home() / ".qb_protocol_multiverse_ranker.json"
TABLET_DIR = Path(__file__).resolve().parent.parent.parent / "The-Tablet-of-Destinies-uppi-m-ti"


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
    source: str = "tablet_oracle"


class MultiverseRanker:
    """Ranks sourced from the Tablet of Destinies oracle - the true ranking tablet."""

    def __init__(self, state_path: Path = RANKER_STATE_PATH):
        self.state_path = state_path
        self.rankings: Dict[str, List[RankedAddress]] = {env: [] for env in ["timeline", "plane", "realm", "environment", "dimension", "void", "global"]}
        self._lock = threading.Lock()
        self._btc_usd = 50000.0
        self._tablet_rankings: Dict[str, List[Dict[str, Any]]] = {}
        self._load()
        self._sync_from_tablet()

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
                    "tablet_synced": datetime.utcnow().isoformat() + "Z",
                }, f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save ranker state: %s", exc)

    def _sync_from_tablet(self):
        """Sync rankings from the Tablet of Destinies oracle."""
        try:
            sys.path.insert(0, str(TABLET_DIR / "probe-sequence"))
            from brain_mesh_chain import BrainMeshChain
            brain_mesh = BrainMeshChain(state_path=str(TABLET_DIR / "probe-sequence" / "brain_mesh_chain_state.json"))
            state = brain_mesh.get_state()
            neural_nets = state.get("neural_nets", {})
            highest_bound = state.get("highest_bound")
            
            tablet_rankings = {}
            for net_id, net_data in neural_nets.items():
                if isinstance(net_data, dict):
                    env_type = net_data.get("environment_type", "global")
                    env_id = net_data.get("environment_id", "")
                    address = net_data.get("btc_public_address", "")
                    user_id = net_data.get("user_id", "")
                    node_id = net_data.get("node_id", "")
                    sats = int(net_data.get("sats", 0))
                    
                    if address and sats > 0:
                        env_key = env_type if env_type in self.rankings else "global"
                        if env_key not in tablet_rankings:
                            tablet_rankings[env_key] = []
                        tablet_rankings[env_key].append({
                            "address": address,
                            "user_id": user_id,
                            "node_id": node_id,
                            "environment_type": env_type,
                            "environment_id": env_id,
                            "sats": sats,
                            "verified": True,
                            "source": "tablet_oracle",
                        })
            
            for env_key, entries in tablet_rankings.items():
                entries.sort(key=lambda x: x["sats"], reverse=True)
                for idx, entry in enumerate(entries):
                    entry["rank"] = idx + 1
                    entry["btc_value_usd"] = (entry["sats"] / 100000000.0) * self._btc_usd
                    entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
            
            with self._lock:
                self._tablet_rankings = tablet_rankings
                for env_key, entries in tablet_rankings.items():
                    self.rankings[env_key] = [RankedAddress(**e) for e in entries]
                self._save()
            
            LOG.info("Synced rankings from Tablet of Destinies oracle: %d environments", len(tablet_rankings))
            return True
        except Exception as exc:
            LOG.warning("Tablet sync failed: %s", exc)
            return False

    def submit_address(self, address: str, user_id: str, node_id: str, environment_type: str, environment_id: str, sats: int, verified: bool = False) -> RankedAddress:
        """Submit address to tablet oracle for authoritative ranking."""
        try:
            sys.path.insert(0, str(TABLET_DIR / "probe-sequence"))
            from brain_mesh_chain import BrainMeshChain
            brain_mesh = BrainMeshChain(state_path=str(TABLET_DIR / "probe-sequence" / "brain_mesh_chain_state.json"))
            
            neural_net_entry = {
                "btc_public_address": address,
                "user_id": user_id,
                "node_id": node_id,
                "environment_type": environment_type,
                "environment_id": environment_id,
                "sats": sats,
                "submitted_at": datetime.utcnow().isoformat() + "Z",
            }
            
            state = brain_mesh.get_state()
            neural_nets = state.get("neural_nets", {})
            net_key = f"{user_id}:{node_id}:{environment_type}:{environment_id}"
            neural_nets[net_key] = neural_net_entry
            brain_mesh._state["neural_nets"] = neural_nets
            brain_mesh.save()
            
            self._sync_from_tablet()
            
            env_key = environment_type if environment_type in self.rankings else "global"
            with self._lock:
                for r in self.rankings.get(env_key, []):
                    if r.address == address and r.node_id == node_id:
                        return r
        except Exception as exc:
            LOG.warning("Tablet submission failed: %s", exc)
        
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
            source="local_fallback",
        )
        with self._lock:
            env_key = environment_type if environment_type in self.rankings else "global"
            self.rankings[env_key].append(ranked)
            self.rankings[env_key].sort(key=lambda r: r.sats, reverse=True)
            for idx, r in enumerate(self.rankings[env_key]):
                r.rank = idx + 1
            self._save()
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
                "tablet_synced": bool(self._tablet_rankings),
                "source": "tablet_oracle",
            }


multiverse_ranker = MultiverseRanker()

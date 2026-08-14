#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Wallet
Virtual wallet with BTC/credit conversion, cloud space backing, and on-chain distribution.
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

LOG = logging.getLogger("qb_protocol.mesh_rewards.wallet")

WALLET_PATH = Path.home() / ".qb_protocol_mesh_wallet.json"


@dataclass
class WalletBalance:
    device_id: str
    credits: float
    btc_sats: int
    cloud_space_bytes: int
    max_capacity_bytes: int
    last_conversion_rate: float
    updated_at: str


class RewardWallet:
    """Virtual wallet backed by device cloud space and blockchain rates."""

    def __init__(self, state_path: Path = WALLET_PATH):
        self.state_path = state_path
        self.balances: Dict[str, WalletBalance] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                for device_id, balance in data.get("balances", {}).items():
                    self.balances[device_id] = WalletBalance(**balance)
                LOG.info("Loaded wallet balances for %d devices", len(self.balances))
            except Exception as exc:
                LOG.warning("Failed to load wallet: %s", exc)

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "balances": {k: asdict(v) for k, v in self.balances.items()},
                }, f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save wallet: %s", exc)

    def _get_cloud_space(self, device_id: str) -> tuple[int, int]:
        used = 0
        max_capacity = 0
        try:
            from qb_protocol.mesh_rewards.device_identity import device_identity
            identity = device_identity.get_identity()
            if identity and identity.get("device_id") == device_id:
                used = 1024 * 1024 * 1024
                max_capacity = 5 * 1024 * 1024 * 1024
        except Exception:
            pass
        return used, max_capacity

    def initialize_device(self, device_id: str) -> WalletBalance:
        used, max_capacity = self._get_cloud_space(device_id)
        with self._lock:
            if device_id not in self.balances:
                from mesh_rewards.blockchain_rates import blockchain_rates
                rates = blockchain_rates.get_rates()
                self.balances[device_id] = WalletBalance(
                    device_id=device_id,
                    credits=0.0,
                    btc_sats=0,
                    cloud_space_bytes=used,
                    max_capacity_bytes=max_capacity,
                    last_conversion_rate=rates.get("sats_per_credit", 0),
                    updated_at=datetime.utcnow().isoformat() + "Z",
                )
                self._save()
        return self.balances[device_id]

    def credit(self, device_id: str, amount: float) -> Optional[WalletBalance]:
        from mesh_rewards.blockchain_rates import blockchain_rates
        with self._lock:
            if device_id not in self.balances:
                self.initialize_device(device_id)
            b = self.balances[device_id]
            b.credits += amount
            b.btc_sats = blockchain_rates.convert_credits_to_sats(b.credits)
            b.updated_at = datetime.utcnow().isoformat() + "Z"
            self._save()
        LOG.info("Wallet credited: %s +%.2f credits", device_id, amount)
        return self.balances[device_id]

    def debit(self, device_id: str, amount: float) -> bool:
        with self._lock:
            if device_id not in self.balances or self.balances[device_id].credits < amount:
                return False
            from mesh_rewards.blockchain_rates import blockchain_rates
            self.balances[device_id].credits -= amount
            self.balances[device_id].btc_sats = blockchain_rates.convert_credits_to_sats(self.balances[device_id].credits)
            self.balances[device_id].updated_at = datetime.utcnow().isoformat() + "Z"
            self._save()
        LOG.info("Wallet debited: %s -%.2f credits", device_id, amount)
        return True

    def get_balance(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if device_id not in self.balances:
                return None
            b = self.balances[device_id]
            return {
                "device_id": b.device_id,
                "credits": b.credits,
                "btc_sats": b.btc_sats,
                "btc_balance": b.btc_sats / 100000000.0,
                "cloud_space_bytes": b.cloud_space_bytes,
                "max_capacity_bytes": b.max_capacity_bytes,
                "last_conversion_rate": b.last_conversion_rate,
                "updated_at": b.updated_at,
            }

    def get_all_balances(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self.get_balance(did) for did in self.balances]

    def convert_to_btc(self, device_id: str, credits: float) -> Dict[str, Any]:
        from mesh_rewards.blockchain_rates import blockchain_rates
        with self._lock:
            if device_id not in self.balances or self.balances[device_id].credits < credits:
                return {"error": "insufficient_balance"}
            self.balances[device_id].credits -= credits
            sats = blockchain_rates.convert_credits_to_sats(credits)
            self.balances[device_id].btc_sats += sats
            self.balances[device_id].updated_at = datetime.utcnow().isoformat() + "Z"
            self._save()
        LOG.info("Converted %.2f credits to %d sats for %s", credits, sats, device_id)
        return {
            "device_id": device_id,
            "converted_credits": credits,
            "sats_added": sats,
            "btc_added": sats / 100000000.0,
            "new_balance": self.get_balance(device_id),
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "device_count": len(self.balances),
            }


reward_wallet = RewardWallet()

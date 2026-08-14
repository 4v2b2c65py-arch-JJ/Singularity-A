#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Ledger
Distributed ledger for reward transactions.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

LOG = logging.getLogger("qb_protocol.mesh_rewards.ledger")


@dataclass
class LedgerEntry:
    entry_id: str
    device_id: str
    transaction_type: str
    amount: float
    token_type: str
    peer_device_id: Optional[str]
    signature: str
    timestamp: str


class RewardLedger:
    """Distributed ledger for mesh reward transactions."""

    def __init__(self):
        self.entries: List[LedgerEntry] = []
        self._lock = threading.Lock()

    def _sign(self, entry: LedgerEntry) -> str:
        payload = f"{entry.device_id}:{entry.transaction_type}:{entry.amount}:{entry.timestamp}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def record_transaction(self, device_id: str, transaction_type: str, amount: float, token_type: str = "credit", peer_device_id: Optional[str] = None) -> LedgerEntry:
        entry = LedgerEntry(
            entry_id=str(uuid.uuid4()),
            device_id=device_id,
            transaction_type=transaction_type,
            amount=amount,
            token_type=token_type,
            peer_device_id=peer_device_id,
            signature="",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        entry.signature = self._sign(entry)
        with self._lock:
            self.entries.append(entry)
        LOG.info("Ledger entry: %s %s %.2f %s", device_id, transaction_type, amount, token_type)
        return entry

    def get_entries(self, device_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            entries = list(self.entries)
        if device_id:
            entries = [e for e in entries if e.device_id == device_id]
        return [asdict(e) for e in entries[-limit:]]

    def get_balance(self, device_id: str) -> float:
        balance = 0.0
        with self._lock:
            for e in self.entries:
                if e.device_id == device_id:
                    if e.transaction_type in ("credit", "reward", "transfer_in"):
                        balance += e.amount
                    elif e.transaction_type in ("debit", "transfer_out"):
                        balance -= e.amount
        return balance

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_entries": len(self.entries),
            }


reward_ledger = RewardLedger()

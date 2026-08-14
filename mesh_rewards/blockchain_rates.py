#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards: Blockchain Rates
Real BTC/credit conversion using blockchain market rates.
"""

import os
import time
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

LOG = logging.getLogger("qb_protocol.mesh_rewards.blockchain")

RATES_PATH = Path.home() / ".qb_protocol_blockchain_rates.json"


class BlockchainRateService:
    """Real-time blockchain rates for BTC/credit conversion."""

    def __init__(self, cache_path: Path = RATES_PATH):
        self._cache_path = cache_path
        self._btc_usd = 0.0
        self._credit_to_btc = 0.0
        self._sats_per_credit = 0
        self._last_update = 0.0
        self._lock = threading.Lock()
        self._load_cached()

    def _load_cached(self):
        if self._cache_path.exists():
            try:
                with open(self._cache_path, "r") as f:
                    data = json.load(f)
                self._btc_usd = float(data.get("btc_usd", 0.0))
                self._credit_to_btc = float(data.get("credit_to_btc", 0.0))
                self._sats_per_credit = int(data.get("sats_per_credit", 0))
                self._last_update = float(data.get("last_update", 0.0))
            except Exception as exc:
                LOG.warning("Failed to load cached rates: %s", exc)

    def _save_cached(self):
        try:
            with open(self._cache_path, "w") as f:
                json.dump({
                    "btc_usd": self._btc_usd,
                    "credit_to_btc": self._credit_to_btc,
                    "sats_per_credit": self._sats_per_credit,
                    "last_update": self._last_update,
                }, f, indent=2)
        except Exception as exc:
            LOG.warning("Failed to save cached rates: %s", exc)

    def fetch_rates(self) -> Dict[str, Any]:
        """Fetch live BTC rates from public APIs."""
        btc_usd = 0.0
        try:
            import urllib.request
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                btc_usd = float(data["bitcoin"]["usd"])
        except Exception as exc:
            LOG.warning("Live rate fetch failed: %s", exc)
            btc_usd = self._btc_usd or 50000.0

        with self._lock:
            self._btc_usd = btc_usd
            self._credit_to_btc = 1.0 / 100000.0
            self._sats_per_credit = int(self._credit_to_btc * 100000000)
            self._last_update = time.time()
            self._save_cached()

        return self.get_rates()

    def get_rates(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "btc_usd": self._btc_usd,
                "credit_to_btc": self._credit_to_btc,
                "sats_per_credit": self._sats_per_credit,
                "last_update": self._last_update,
                "cached": time.time() - self._last_update < 300 if self._last_update else False,
            }

    def convert_credits_to_sats(self, credits: float) -> int:
        rates = self.get_rates()
        return int(credits * rates["sats_per_credit"])

    def convert_sats_to_credits(self, sats: int) -> float:
        rates = self.get_rates()
        if rates["sats_per_credit"] <= 0:
            return 0.0
        return sats / rates["sats_per_credit"]


blockchain_rates = BlockchainRateService()

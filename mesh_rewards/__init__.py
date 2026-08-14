#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards Package
Cross-device NFC rewards with virtual BTC/credit conversion, investigation, and on-chain distribution.
"""

from .device_identity import DeviceIdentity, device_identity
from .nfc_bridge import NFCBridge, nfc_bridge
from .reward_engine import RewardEngine, reward_engine
from .wallet import RewardWallet, reward_wallet
from .icloud_sync import ICloudSync, icloud_sync
from .ledger import RewardLedger, reward_ledger
from .blockchain_rates import BlockchainRateService, blockchain_rates
from .investigation import InvestigationAgent, investigation_agent
from .watchdog import Watchdog, watchdog
from .celestial_nodes import CelestialNodeManager, celestial_node_manager
from .multiverse_ranker import MultiverseRanker, multiverse_ranker
from .fund_reasoning import FundReasoningAgent, fund_reasoning_agent
from .api.routes import router as mesh_rewards_router

__all__ = [
    "DeviceIdentity",
    "device_identity",
    "NFCBridge",
    "nfc_bridge",
    "RewardEngine",
    "reward_engine",
    "RewardWallet",
    "reward_wallet",
    "ICloudSync",
    "icloud_sync",
    "RewardLedger",
    "reward_ledger",
    "BlockchainRateService",
    "blockchain_rates",
    "InvestigationAgent",
    "investigation_agent",
    "Watchdog",
    "watchdog",
    "CelestialNodeManager",
    "celestial_node_manager",
    "MultiverseRanker",
    "multiverse_ranker",
    "FundReasoningAgent",
    "fund_reasoning_agent",
    "mesh_rewards_router",
]

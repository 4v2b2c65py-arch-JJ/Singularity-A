#!/usr/bin/env python3
"""
QB Protocol - Mesh Rewards API Routes
NFC, wallet, rewards, blockchain, investigation, watchdog endpoints.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from qb_protocol.mesh_rewards.device_identity import device_identity
    from qb_protocol.mesh_rewards.nfc_bridge import nfc_bridge
    from qb_protocol.mesh_rewards.reward_engine import reward_engine
    from qb_protocol.mesh_rewards.wallet import reward_wallet
    from qb_protocol.mesh_rewards.icloud_sync import icloud_sync
    from qb_protocol.mesh_rewards.ledger import reward_ledger
    from qb_protocol.mesh_rewards.blockchain_rates import blockchain_rates
    from qb_protocol.mesh_rewards.investigation import investigation_agent
    from qb_protocol.mesh_rewards.watchdog import watchdog
    from qb_protocol.mesh_rewards.celestial_nodes import celestial_node_manager
    from qb_protocol.mesh_rewards.multiverse_ranker import multiverse_ranker
    from qb_protocol.mesh_rewards.fund_reasoning import fund_reasoning_agent
    HAS_MESH_REWARDS = True
except ImportError:
    try:
        from mesh_rewards.device_identity import device_identity
        from mesh_rewards.nfc_bridge import nfc_bridge
        from mesh_rewards.reward_engine import reward_engine
        from mesh_rewards.wallet import reward_wallet
        from mesh_rewards.icloud_sync import icloud_sync
        from mesh_rewards.ledger import reward_ledger
        from mesh_rewards.blockchain_rates import blockchain_rates
        from mesh_rewards.investigation import investigation_agent
        from mesh_rewards.watchdog import watchdog
        from mesh_rewards.celestial_nodes import celestial_node_manager
        from mesh_rewards.multiverse_ranker import multiverse_ranker
        from mesh_rewards.fund_reasoning import fund_reasoning_agent
        HAS_MESH_REWARDS = True
    except ImportError:
        HAS_MESH_REWARDS = False

router = APIRouter(prefix="/mesh-rewards", tags=["mesh-rewards"])


@router.get("/device/identity")
def get_device_identity():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    identity = device_identity.get_identity()
    if not identity:
        identity = device_identity.detect_from_icloud()
    return identity


@router.post("/device/verify")
def verify_device_identity():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    valid = device_identity.verify_identity()
    return {"verified": valid, "identity": device_identity.get_identity()}


@router.get("/nfc/status")
def nfc_status():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return nfc_bridge.get_status()


@router.get("/nfc/peers")
def get_nfc_peers():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"peers": nfc_bridge.get_peers()}


@router.post("/nfc/transfer")
def nfc_transfer(body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    to_device = body.get("to_device", "")
    amount = float(body.get("amount", 0))
    token_type = body.get("token_type", "credit")
    if not to_device or amount <= 0:
        return {"error": "invalid_transfer"}
    transfer = nfc_bridge.initiate_transfer(to_device, amount, token_type)
    reward_ledger.record_transaction("self", "transfer_out", amount, token_type, to_device)
    return asdict(transfer)


@router.get("/rewards/status")
def rewards_status():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return reward_engine.get_status()


@router.get("/rewards/leaderboard")
def rewards_leaderboard(window_seconds: float = 86400.0):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"leaderboard": reward_engine.get_leaderboard(window_seconds)}


@router.post("/rewards/distribute")
def distribute_rewards(body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    device_id = body.get("device_id", "")
    contribution_type = body.get("contribution_type", "ai_inference")
    duration_seconds = float(body.get("duration_seconds", 0))
    data_amount = float(body.get("data_amount", 0))
    cloud_space_bytes = int(body.get("cloud_space_bytes", 0))
    if not device_id:
        return {"error": "invalid_params"}
    contribution = reward_engine.record_contribution(device_id, contribution_type, duration_seconds, data_amount, cloud_space_bytes)
    score = reward_engine.calculate_device_score(device_id)
    trial = reward_engine.initiate_reward_trial(device_id, score)
    reward_wallet.initialize_device(device_id)
    return {
        "contribution": asdict(contribution),
        "trial": asdict(trial),
        "score": score,
    }


@router.post("/rewards/trial/{payout_id}/resolve")
def resolve_trial(payout_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    approved = bool(body.get("approved", False))
    failure_reason = body.get("failure_reason", "")
    payout = reward_engine.resolve_trial(payout_id, approved, failure_reason)
    if not payout:
        return {"error": "trial_not_found"}
    if approved:
        reward_wallet.credit(payout.device_id, payout.credit_amount)
        reward_ledger.record_transaction(payout.device_id, "reward", payout.credit_amount, "credit")
        reward_engine.distribute_reward(payout_id)
    return asdict(payout)


@router.get("/wallet/{device_id}")
def get_wallet_balance(device_id: str):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    balance = reward_wallet.get_balance(device_id)
    if not balance:
        return {"error": "wallet_not_found"}
    return balance


@router.post("/wallet/{device_id}/convert")
def convert_to_btc(device_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    credits = float(body.get("credits", 0))
    if credits <= 0:
        return {"error": "invalid_amount"}
    result = reward_wallet.convert_to_btc(device_id, credits)
    if "error" in result:
        return result
    reward_ledger.record_transaction(device_id, "convert", credits, "credit_to_btc")
    return result


@router.get("/wallet/balances")
def get_all_balances():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"balances": reward_wallet.get_all_balances()}


@router.get("/blockchain/rates")
def get_blockchain_rates():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return blockchain_rates.get_rates()


@router.post("/blockchain/rates/refresh")
def refresh_blockchain_rates():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return blockchain_rates.fetch_rates()


@router.post("/investigation/start")
def start_investigation(body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    device_id = body.get("device_id", "")
    trigger = body.get("trigger", "manual")
    evidence = body.get("evidence", {})
    if not device_id:
        return {"error": "device_id_required"}
    case = investigation_agent.start_investigation(device_id, trigger, evidence)
    return asdict(case)


@router.post("/investigation/{case_id}/evaluate")
def evaluate_investigation(case_id: str):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return investigation_agent.evaluate_eligibility(case_id)


@router.get("/investigation/cases/{device_id}")
def get_investigation_cases(device_id: str):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"cases": investigation_agent.get_cases(device_id)}


@router.get("/watchdog/alerts")
def get_watchdog_alerts(limit: int = 100):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"alerts": watchdog.get_alerts(limit)}


@router.get("/watchdog/status")
def watchdog_status():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return watchdog.get_status()


@router.get("/icloud/status")
def icloud_status():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"available": icloud_sync.is_available()}


@router.post("/icloud/sync")
def icloud_sync_state():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    data = {
        "wallet": reward_wallet.get_all_balances(),
        "ledger": reward_ledger.get_entries(limit=100),
        "peers": nfc_bridge.get_peers(),
    }
    success = icloud_sync.sync(data)
    return {"synced": success}


@router.get("/ledger/{device_id}")
def get_ledger(device_id: str, limit: int = 100):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"entries": reward_ledger.get_entries(device_id, limit)}


@router.post("/celestial/nodes/register")
def register_celestial_node(body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    user_id = body.get("user_id", "")
    environment_type = body.get("environment_type", "timeline")
    environment_id = body.get("environment_id", "")
    device_id = body.get("device_id", "")
    btc_public_address = body.get("btc_public_address", "")
    metadata = body.get("metadata", {})
    if not user_id or not environment_type or not device_id or not btc_public_address:
        return {"error": "missing_required_fields"}
    node = celestial_node_manager.register_node(user_id, environment_type, environment_id, device_id, btc_public_address, metadata)
    return asdict(node)


@router.get("/celestial/nodes/user/{user_id}")
def get_celestial_nodes_by_user(user_id: str):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"nodes": celestial_node_manager.get_nodes_by_user(user_id)}


@router.get("/celestial/nodes/environment/{environment_type}")
def get_celestial_nodes_by_environment(environment_type: str, environment_id: str = ""):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"nodes": celestial_node_manager.get_nodes_by_environment(environment_type, environment_id)}


@router.post("/celestial/nodes/link")
def link_celestial_nodes(body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    node_a = body.get("node_a", "")
    node_b = body.get("node_b", "")
    if not node_a or not node_b:
        return {"error": "missing_nodes"}
    celestial_node_manager.link_nodes(node_a, node_b)
    return {"linked": True, "node_a": node_a, "node_b": node_b}


@router.get("/celestial/nodes/{node_id}/linked")
def get_linked_celestial_nodes(node_id: str):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"linked_nodes": celestial_node_manager.get_linked_nodes(node_id)}


@router.get("/multiverse/leaderboard")
def multiverse_leaderboard(environment_type: str = "global", limit: int = 100):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"leaderboard": multiverse_ranker.get_leaderboard(environment_type, limit)}


@router.get("/multiverse/rank/user/{user_id}")
def get_multiverse_rank(user_id: str, environment_type: str = "global"):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    rank = multiverse_ranker.get_user_rank(user_id, environment_type)
    if not rank:
        return {"error": "user_not_ranked"}
    return rank


@router.post("/multiverse/address/submit")
def submit_btc_address(body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    address = body.get("address", "")
    user_id = body.get("user_id", "")
    node_id = body.get("node_id", "")
    environment_type = body.get("environment_type", "global")
    environment_id = body.get("environment_id", "")
    sats = int(body.get("sats", 0))
    verified = bool(body.get("verified", False))
    if not address or not user_id or not node_id or sats <= 0:
        return {"error": "missing_required_fields"}
    ranked = multiverse_ranker.submit_address(address, user_id, node_id, environment_type, environment_id, sats, verified)
    return asdict(ranked)


@router.get("/multiverse/rankings/status")
def multiverse_rankings_status():
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return multiverse_ranker.get_status()


@router.post("/fund/request")
def request_funds(body: Dict[str, Any] = Body(...)):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    device_id = body.get("device_id", "")
    user_id = body.get("user_id", "")
    amount_requested = float(body.get("amount_requested", 0))
    reason = body.get("reason", "")
    metrics = body.get("metrics", {})
    if not device_id or not user_id or amount_requested <= 0:
        return {"error": "missing_required_fields"}
    request = fund_reasoning_agent.evaluate_fund_request(device_id, user_id, amount_requested, reason, metrics)
    return asdict(request)


@router.get("/fund/requests/{user_id}")
def get_fund_requests(user_id: str):
    if not HAS_MESH_REWARDS:
        return {"error": "mesh_rewards_unavailable"}
    return {"requests": fund_reasoning_agent.get_requests(user_id)}


@router.get("/")
def mesh_rewards_root():
    return RedirectResponse(url="/mesh-rewards/device/identity")

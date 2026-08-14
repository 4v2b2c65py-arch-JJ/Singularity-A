#!/usr/bin/env python3
"""
QB Protocol - VR Warp API Routes
"""

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.vr_quest.warp.core.resonance import resonance_agent
    from qb_protocol.vr_quest.warp.core.warp_engine import warp_engine
    from qb_protocol.vr_quest.warp.core.proximity_guard import proximity_guard
    from qb_protocol.vr_quest.warp.core.amplitude import amplitude_pack
    from qb_protocol.vr_quest.warp.core.barrier import barrier_manager
    from qb_protocol.vr_quest.warp.core.security import security_checker
    from qb_protocol.vr_quest.warp.core.solar_sync import solar_sync
    HAS_WARP = True
except ImportError:
    HAS_WARP = False

router = APIRouter(prefix="/warp", tags=["warp"])


@router.get("/status")
def warp_status():
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    return {
        "resonance": resonance_agent.get_status(),
        "warp_engine": warp_engine.get_status(),
        "proximity": proximity_guard.get_status(),
        "amplitude": amplitude_pack.get_status(),
        "barrier": barrier_manager.get_status(),
        "security": security_checker.get_status(),
        "solar": solar_sync.get_status(),
    }


@router.post("/resonance/schemas")
def create_schema(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    schema = resonance_agent.register_schema(
        name=body.get("name", "Default Schema"),
        frequency=body.get("frequency", 1.0),
        amplitude=body.get("amplitude", 1.0),
        phase=body.get("phase", 0.0),
        metadata=body.get("metadata"),
    )
    return schema


@router.post("/resonance/agents")
def create_agent(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    agent = resonance_agent.create_agent(
        name=body.get("name", "Default Agent"),
        schema_ids=body.get("schema_ids", []),
        steering_power=body.get("steering_power", 1.0),
        reach=body.get("reach", 1.0),
        guardian_status=body.get("guardian_status", True),
        metadata=body.get("metadata"),
    )
    return agent


@router.post("/resonance/steer")
def steer_agent(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    return resonance_agent.steer(
        agent_id=body.get("agent_id", ""),
        target_frequency=body.get("target_frequency", 1.0),
        target_amplitude=body.get("target_amplitude", 1.0),
    )


@router.post("/calculate")
def calculate_warp(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    warp = warp_engine.calculate_warp(
        origin=body.get("origin", {"x": 0, "y": 0, "z": 0}),
        target=body.get("target", {"x": 1, "y": 1, "z": 1}),
        amplitude=body.get("amplitude", 1.0),
    )
    return warp


@router.post("/proximity/enforce")
def enforce_proximity(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    state = proximity_guard.enforce_proximity(
        warp_id=body.get("warp_id", ""),
        origin=body.get("origin", {"x": 0, "y": 0, "z": 0}),
        target=body.get("target", {"x": 1, "y": 1, "z": 1}),
        max_destruction_risk=body.get("max_destruction_risk", 0.3),
    )
    return state


@router.post("/amplitude/packs")
def create_amplitude_pack(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    pack = amplitude_pack.create_pack(
        warp_id=body.get("warp_id", ""),
        base_amplitude=body.get("base_amplitude", 1.0),
        max_amplitude=body.get("max_amplitude", 2.0),
        metadata=body.get("metadata"),
    )
    return pack


@router.post("/amplitude/adjust")
def adjust_amplitude(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    pack = amplitude_pack.adjust_amplitude(
        pack_id=body.get("pack_id", ""),
        target_amplitude=body.get("target_amplitude", 1.0),
    )
    return pack


@router.post("/barriers")
def register_barrier(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    barrier = barrier_manager.register_barrier(
        realm_id=body.get("realm_id", ""),
        barrier_type=body.get("barrier_type", "default"),
        strength=body.get("strength", 1.0),
        conditions=body.get("conditions", []),
    )
    return barrier


@router.post("/permits")
def issue_permit(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    permit = barrier_manager.issue_permit(
        realm_id=body.get("realm_id", ""),
        requester_id=body.get("requester_id", "anonymous"),
        ttl_seconds=body.get("ttl_seconds", 3600),
        conditions=body.get("conditions", []),
    )
    return permit


@router.get("/permits")
def get_permits(realm_id: Optional[str] = None):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    return barrier_manager.get_permits(realm_id)


@router.post("/security/check")
def run_security_check(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    check = security_checker.run_security_check(
        warp_id=body.get("warp_id", ""),
        check_type=body.get("check_type", "general"),
        details=body.get("details", {}),
    )
    return check


@router.get("/security/checks")
def get_security_checks(warp_id: Optional[str] = None, limit: int = 100):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    return security_checker.get_checks(warp_id, limit)


@router.post("/solar/cycles")
def create_solar_cycle(body: Dict[str, Any] = Body(...)):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    cycle = solar_sync.create_cycle(
        period=body.get("period", 24.0),
        amplitude=body.get("amplitude", 1.0),
        metadata=body.get("metadata"),
    )
    return cycle


@router.get("/solar/cycles/{cycle_id}/sync")
def get_sync_window(cycle_id: str):
    if not HAS_WARP:
        return {"error": "warp_unavailable"}
    return solar_sync.get_sync_window(cycle_id)

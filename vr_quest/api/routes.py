#!/usr/bin/env python3
"""
QB Protocol - VR Quest API Routes
"""

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.vr_quest.core.regions import region_manager
    from qb_protocol.vr_quest.core.session import session_manager
    from qb_protocol.vr_quest.core.content import content_manager
    from qb_protocol.vr_quest.core.diagnostics import network_diagnostics
    from qb_protocol.vr_quest.companion.oscquery import oscquery_bridge
    from qb_protocol.vr_quest.companion.slimevr import slimevr_bridge
    from qb_protocol.vr_quest.companion.tracking import tracking_manager
    from qb_protocol.vr_quest.companion.auto_reconnect import auto_reconnect
    from qb_protocol.vr_quest.companion.service import companion_service
    from qb_protocol.vr_quest.quest.config import quest_config
    from qb_protocol.vr_quest.quest.avatar import avatar_manager
    HAS_VR = True
except ImportError:
    HAS_VR = False

router = APIRouter(prefix="/vr", tags=["vr"])


@router.get("/status")
def vr_status():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return {
        "regions": region_manager.get_status(),
        "sessions": session_manager.get_status(),
        "content": content_manager.get_status(),
        "diagnostics": network_diagnostics.get_status(),
        "tracking": tracking_manager.get_status(),
        "service": companion_service.get_status(),
        "slimevr": slimevr_bridge.get_status(),
        "oscquery": oscquery_bridge.get_status(),
        "reconnect": auto_reconnect.get_status(),
        "avatars": avatar_manager.get_status(),
    }


@router.get("/regions")
def get_regions():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return region_manager.get_regions()


@router.post("/regions")
def create_region(body: Dict[str, Any] = Body(...)):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    region = region_manager.register_region(
        name=body.get("name", "Unknown"),
        code=body.get("code", "UNK"),
        endpoint=body.get("endpoint", ""),
        capacity=body.get("capacity", 1000),
        metadata=body.get("metadata"),
    )
    return region


@router.get("/regions/best")
def get_best_region(preferred: Optional[str] = None):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    region = region_manager.select_best_region(preferred)
    return region if region else {"error": "no_healthy_region"}


@router.post("/regions/failover")
def failover_region():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    region = region_manager.failover()
    return region if region else {"error": "failover_failed"}


@router.get("/sessions")
def get_sessions():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return session_manager.get_active_sessions()


@router.post("/sessions")
def create_session(body: Dict[str, Any] = Body(...)):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    session = session_manager.create_session(
        user_id=body.get("user_id", "anonymous"),
        region_id=body.get("region_id", ""),
        ttl_seconds=body.get("ttl_seconds", 86400),
    )
    return session


@router.get("/content")
def get_content():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return content_manager.get_manifests()


@router.post("/content")
def create_content(body: Dict[str, Any] = Body(...)):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    manifest = content_manager.create_manifest(
        name=body.get("name", "Unknown"),
        version=body.get("version", "1.0.0"),
        content_path=Path(body.get("content_path", "")),
        minimum_client_version=body.get("minimum_client_version", "1.0.0"),
        supported_devices=body.get("supported_devices", []),
        metadata=body.get("metadata"),
    )
    return manifest


@router.get("/diagnostics/latency")
def test_latency(host: str = "127.0.0.1", port: int = 443):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    result = network_diagnostics.test_latency(host, port)
    return result


@router.get("/diagnostics/connection")
def test_connection(url: str = "https://api.example.com"):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    result = network_diagnostics.test_connection(url)
    return result


@router.get("/oscquery/discover")
def discover_oscquery():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    discoveries = oscquery_bridge.discover_vrchat()
    return {"discoveries": [asdict(d) for d in discoveries]}


@router.get("/oscquery/status")
def oscquery_status():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return oscquery_bridge.get_status()


@router.get("/slimevr/discover")
def discover_slimevr():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    trackers = slimevr_bridge.discover_trackers()
    return {"trackers": [asdict(t) for t in trackers]}


@router.get("/slimevr/status")
def slimevr_status():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return slimevr_bridge.get_status()


@router.post("/tracking/profile")
def set_tracking_profile(body: Dict[str, Any] = Body(...)):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    profile = body.get("profile", 1)
    state = tracking_manager.set_profile(profile)
    return state


@router.get("/tracking/status")
def tracking_status():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return tracking_manager.get_status()


@router.get("/service/status")
def service_status():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return companion_service.get_status()


@router.post("/service/state")
def set_service_state(body: Dict[str, Any] = Body(...)):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    state = body.get("state", "ready")
    status = companion_service.set_state(state)
    return status


@router.get("/quest/config")
def get_quest_config():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    config = quest_config.get_config()
    if not config:
        config = quest_config.initialize()
    return config


@router.get("/quest/budget")
def get_budget_status():
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return quest_config.get_budget_status()


@router.post("/avatars")
def create_avatar(body: Dict[str, Any] = Body(...)):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    avatar = avatar_manager.create_avatar(
        name=body.get("name", "Unknown Avatar"),
        tier=body.get("tier", "quest_standard"),
        metadata=body.get("metadata"),
    )
    return avatar


@router.get("/avatars")
def get_avatars(tier: Optional[str] = None):
    if not HAS_VR:
        return {"error": "vr_unavailable"}
    return avatar_manager.get_avatars(tier)

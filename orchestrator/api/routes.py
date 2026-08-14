#!/usr/bin/env python3
"""
QB Protocol - Orchestrator API Routes
Full agentic sync, boot persistence, auto-update, and device management.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from qb_protocol.orchestrator.agentic_sync import orchestrator
    from qb_protocol.orchestrator.auto_update import auto_updater
    from qb_protocol.orchestrator.keepalive_tcp import keepalive_tcp_manager
    HAS_ORCHESTRATOR = True
except ImportError:
    try:
        from orchestrator.agentic_sync import orchestrator
        from orchestrator.auto_update import auto_updater
        from orchestrator.keepalive_tcp import keepalive_tcp_manager
        HAS_ORCHESTRATOR = True
    except ImportError:
        HAS_ORCHESTRATOR = False

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.get("/status")
def orchestrator_status():
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return orchestrator.get_status()


@router.post("/sync")
def orchestrator_sync(body: Dict[str, Any] = Body(...)):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    direction = body.get("direction", "bidirectional")
    result = orchestrator.sync(direction=direction)
    return result


@router.get("/changes")
def orchestrator_changes(limit: int = 100):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return {"changes": orchestrator.get_changes(limit=limit)}


@router.post("/update")
def orchestrator_update(body: Dict[str, Any] = Body(...)):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    target_version = body.get("target_version")
    result = orchestrator.update(target_version=target_version)
    return result


@router.get("/updates/check")
def check_updates():
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return auto_updater.check_for_updates()


@router.post("/updates/apply")
def apply_update(body: Dict[str, Any] = Body(...)):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    target_version = body.get("target_version")
    result = auto_updater.apply_update(target_version=target_version)
    return result


@router.get("/updates/history")
def update_history(limit: int = 50):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return {"history": auto_updater.get_history(limit=limit)}


@router.post("/service/install")
def install_service():
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return orchestrator.install_service()


@router.post("/service/uninstall")
def uninstall_service():
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return orchestrator.uninstall_service()


@router.get("/service/status")
def service_status():
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return orchestrator.get_service_status()


@router.post("/reboot")
def reboot_device(body: Dict[str, Any] = Body(...)):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    delay = body.get("delay", 0)
    result = orchestrator.reboot_device(delay=delay)
    return result


@router.get("/")
def orchestrator_root():
    return RedirectResponse(url="/orchestrator/status")


@router.get("/keepalive/status")
def keepalive_status():
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    return keepalive_tcp_manager.get_status()


@router.post("/keepalive/clients")
def create_keepalive_client(body: Dict[str, Any] = Body(...)):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    host = body.get("host", "")
    port = int(body.get("port", 0))
    if not host or not port:
        return {"error": "host_and_port_required"}
    client = keepalive_tcp_manager.create_client(
        host=host,
        port=port,
        timeout=body.get("timeout", 5.0),
        keepalive_idle=body.get("keepalive_idle", 60),
        keepalive_interval=body.get("keepalive_interval", 10),
        keepalive_count=body.get("keepalive_count", 3),
        reconnect=body.get("reconnect", True),
        max_reconnect_attempts=body.get("max_reconnect_attempts", 10),
    )
    connected = client.connect()
    return {"client_id": client.client_id, "connected": connected, "config": asdict(client.config)}


@router.post("/keepalive/clients/{client_id}/connect")
def connect_keepalive_client(client_id: str):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    client = keepalive_tcp_manager.get_client(client_id)
    if not client:
        return {"error": "client_not_found"}
    connected = client.connect()
    return {"client_id": client_id, "connected": connected}


@router.post("/keepalive/clients/{client_id}/disconnect")
def disconnect_keepalive_client(client_id: str):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    client = keepalive_tcp_manager.get_client(client_id)
    if not client:
        return {"error": "client_not_found"}
    client.disconnect()
    return {"client_id": client_id, "disconnected": True}


@router.post("/keepalive/clients/{client_id}/heartbeat/start")
def start_keepalive_heartbeat(client_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    client = keepalive_tcp_manager.get_client(client_id)
    if not client:
        return {"error": "client_not_found"}
    interval = float(body.get("interval", 30.0))
    client.start_heartbeat(interval=interval)
    return {"client_id": client_id, "heartbeat_started": True, "interval": interval}


@router.get("/keepalive/clients/{client_id}/state")
def get_keepalive_client_state(client_id: str):
    if not HAS_ORCHESTRATOR:
        return {"error": "orchestrator_unavailable"}
    client = keepalive_tcp_manager.get_client(client_id)
    if not client:
        return {"error": "client_not_found"}
    return client.get_state()

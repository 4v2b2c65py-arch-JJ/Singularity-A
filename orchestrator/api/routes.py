#!/usr/bin/env python3
"""
QB Protocol - Orchestrator API Routes
Full agentic sync, boot persistence, auto-update, and device management.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.orchestrator.agentic_sync import orchestrator
    from qb_protocol.orchestrator.auto_update import auto_updater
    HAS_ORCHESTRATOR = True
except ImportError:
    try:
        from orchestrator.agentic_sync import orchestrator
        from orchestrator.auto_update import auto_updater
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

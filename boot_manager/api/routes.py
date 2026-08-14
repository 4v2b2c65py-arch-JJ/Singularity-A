#!/usr/bin/env python3
"""
QB Protocol - Boot Manager API Routes
Bootloader management, virtual matching, cloud offload.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from qb_protocol.boot_manager.bootloader import boot_manager
    from qb_protocol.boot_manager.cloud_offload import cloud_offload
    HAS_BOOT_MANAGER = True
except ImportError:
    try:
        from boot_manager.bootloader import boot_manager
        from boot_manager.cloud_offload import cloud_offload
        HAS_BOOT_MANAGER = True
    except ImportError:
        HAS_BOOT_MANAGER = False

router = APIRouter(prefix="/boot-manager", tags=["boot-manager"])


@router.get("/status")
def boot_status():
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    return boot_manager.get_status()


@router.post("/images")
def register_boot_image(body: Dict[str, Any] = Body(...)):
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    version = body.get("version", "current")
    platform = body.get("platform", "macos")
    path = body.get("path", str(boot_manager.images_dir / f"boot_{version}.img"))
    is_virtual = body.get("is_virtual", True)
    metadata = body.get("metadata", {})
    image = boot_manager.register_image(version=version, platform=platform, path=path, is_virtual=is_virtual, metadata=metadata)
    return asdict(image)


@router.post("/sessions")
def create_boot_session(body: Dict[str, Any] = Body(...)):
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    active_image_id = body.get("active_image_id", "")
    fallback_image_id = body.get("fallback_image_id")
    if not active_image_id:
        return {"error": "active_image_id_required"}
    session = boot_manager.create_session(active_image_id=active_image_id, fallback_image_id=fallback_image_id)
    return asdict(session)


@router.post("/sessions/{session_id}/swap")
def swap_bootloader(session_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    target_image_id = body.get("target_image_id", "")
    if not target_image_id:
        return {"error": "target_image_id_required"}
    result = boot_manager.swap_bootloader(session_id, target_image_id)
    return result


@router.post("/sessions/{session_id}/rollback")
def rollback_bootloader(session_id: str):
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    result = boot_manager.rollback(session_id)
    return result


@router.get("/images")
def list_boot_images():
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    with boot_manager._lock:
        return {"images": [asdict(img) for img in boot_manager.images.values()]}


@router.get("/sessions")
def list_boot_sessions():
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    with boot_manager._lock:
        return {"sessions": [asdict(sess) for sess in boot_manager.sessions.values()]}


@router.get("/active")
def get_active_boot():
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    return boot_manager.get_active_image() or {"error": "no_active_boot"}


@router.post("/cloud/sync")
def cloud_sync(body: Dict[str, Any] = Body(...)):
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    provider = body.get("provider", "icloud")
    local_path = body.get("local_path", str(Path.home() / ".qb_protocol"))
    cloud_path = body.get("cloud_path", f"qb_protocol/{provider}")
    include_private = body.get("include_private", False)
    sync = cloud_offload.sync_to_cloud(provider=provider, local_path=local_path, cloud_path=cloud_path, include_private=include_private)
    return asdict(sync)


@router.get("/cloud/syncs")
def get_cloud_syncs(limit: int = 50):
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    return {"syncs": cloud_offload.get_syncs(limit=limit)}


@router.get("/cloud/status")
def cloud_status():
    if not HAS_BOOT_MANAGER:
        return {"error": "boot_manager_unavailable"}
    return cloud_offload.get_status()


@router.get("/")
def boot_root():
    return RedirectResponse(url="/boot-manager/status")

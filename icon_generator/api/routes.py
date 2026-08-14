#!/usr/bin/env python3
"""
QB Protocol - Icon Generator API Routes
Automatic icon generation for OS artifacts and applications.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import asdict

try:
    from qb_protocol.icon_generator.generator import icon_generator, IconSpec
    HAS_ICON_GENERATOR = True
except ImportError:
    try:
        from icon_generator.generator import icon_generator, IconSpec
        HAS_ICON_GENERATOR = True
    except ImportError:
        HAS_ICON_GENERATOR = False

router = APIRouter(prefix="/icon-generator", tags=["icon-generator"])


@router.get("/status")
def icon_status():
    if not HAS_ICON_GENERATOR:
        return {"error": "icon_generator_unavailable"}
    return icon_generator.get_status()


@router.post("/generate")
def generate_icon(body: Dict[str, Any] = Body(...)):
    if not HAS_ICON_GENERATOR:
        return {"error": "icon_generator_unavailable"}
    spec = IconSpec(
        name=body.get("name", "icon"),
        size=int(body.get("size", 64)),
        platform=body.get("platform", "macos"),
        background_color=body.get("background_color", "#007AFF"),
        foreground_color=body.get("foreground_color", "#FFFFFF"),
        shape=body.get("shape", "rounded"),
        text=body.get("text"),
        metadata=body.get("metadata", {}),
    )
    icon = icon_generator.generate_icon(spec)
    return asdict(icon)


@router.post("/generate-app-set")
def generate_app_icon_set(body: Dict[str, Any] = Body(...)):
    if not HAS_ICON_GENERATOR:
        return {"error": "icon_generator_unavailable"}
    app_name = body.get("app_name", "App")
    base_color = body.get("base_color", "#007AFF")
    platform = body.get("platform", "macos")
    icons = icon_generator.generate_app_icon_set(app_name=app_name, base_color=base_color, platform=platform)
    return {"icons": [asdict(icon) for icon in icons]}


@router.get("/icons")
def list_icons(limit: int = 50):
    if not HAS_ICON_GENERATOR:
        return {"error": "icon_generator_unavailable"}
    return {"icons": icon_generator.get_icons(limit=limit)}


@router.get("/icons/{icon_id}")
def get_icon(icon_id: str):
    if not HAS_ICON_GENERATOR:
        return {"error": "icon_generator_unavailable"}
    icon = icon_generator.get_icon(icon_id)
    if not icon:
        return {"error": "icon_not_found"}
    return icon


@router.get("/icons/{icon_id}/download")
def download_icon(icon_id: str):
    if not HAS_ICON_GENERATOR:
        return {"error": "icon_generator_unavailable"}
    icon = icon_generator.get_icon(icon_id)
    if not icon:
        return {"error": "icon_not_found"}
    path = Path(icon["path"])
    if not path.exists():
        return {"error": "icon_file_not_found"}
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.get("/")
def icon_root():
    return RedirectResponse(url="/icon-generator/status")

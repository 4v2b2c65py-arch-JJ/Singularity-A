#!/usr/bin/env python3
"""
QB Protocol - Adaptive Learning API Routes
Keyboard learning, emoji generation, password management.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from qb_protocol.adaptive_learning.keyboard import adaptive_keyboard
    from qb_protocol.adaptive_learning.emoji import emoji_generator
    from qb_protocol.adaptive_learning.passwords import password_manager
    HAS_ADAPTIVE = True
except ImportError:
    try:
        from adaptive_learning.keyboard import adaptive_keyboard
        from adaptive_learning.emoji import emoji_generator
        from adaptive_learning.passwords import password_manager
        HAS_ADAPTIVE = True
    except ImportError:
        HAS_ADAPTIVE = False

router = APIRouter(prefix="/adaptive", tags=["adaptive"])


@router.get("/status")
def adaptive_status():
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    return {
        "keyboard": adaptive_keyboard.get_status(),
        "emoji": emoji_generator.get_status(),
        "passwords": password_manager.get_status(),
    }


@router.post("/keyboard/event")
def record_key_event(body: Dict[str, Any] = Body(...)):
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    user_id = body.get("user_id", "default")
    key = body.get("key", "")
    event_type = body.get("event_type", "press")
    duration = float(body.get("duration", 0.1))
    pressure = float(body.get("pressure", 0.5))
    context = body.get("context", {})
    if not key:
        return {"error": "key_required"}
    event = adaptive_keyboard.record_key_event(user_id=user_id, key=key, event_type=event_type, duration=duration, pressure=pressure, context=context)
    return asdict(event)


@router.post("/keyboard/learn")
def learn_keyboard_pattern(body: Dict[str, Any] = Body(...)):
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    user_id = body.get("user_id", "default")
    pattern = adaptive_keyboard.learn_pattern(user_id=user_id)
    return asdict(pattern)


@router.post("/keyboard/predict")
def predict_next_key(body: Dict[str, Any] = Body(...)):
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    user_id = body.get("user_id", "default")
    current_keys = body.get("current_keys", [])
    predicted = adaptive_keyboard.predict_next_key(user_id=user_id, current_keys=current_keys)
    return {"predicted_key": predicted}


@router.post("/emoji/profile")
def create_emoji_profile(body: Dict[str, Any] = Body(...)):
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    user_id = body.get("user_id", "default")
    style = body.get("style", "default")
    profile = emoji_generator.create_profile(user_id=user_id, style=style)
    return asdict(profile)


@router.get("/emoji/profile/{user_id}")
def get_emoji_profile(user_id: str):
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    profile = emoji_generator.get_profile(user_id=user_id)
    if not profile:
        return {"error": "profile_not_found"}
    return profile


@router.post("/passwords")
def add_password(body: Dict[str, Any] = Body(...)):
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    user_id = body.get("user_id", "default")
    service = body.get("service", "")
    username = body.get("username", "")
    password = body.get("password", "")
    url = body.get("url")
    notes = body.get("notes")
    if not service or not username or not password:
        return {"error": "service_username_password_required"}
    entry = password_manager.add_password(user_id=user_id, service=service, username=username, password=password, url=url, notes=notes)
    result = asdict(entry)
    result.pop("password_encrypted", None)
    return result


@router.get("/passwords/{user_id}/{service}")
def get_password(user_id: str, service: str):
    if not HAS_ADAPTIVE:
        return {"error": "adaptive_unavailable"}
    entry = password_manager.get_password(user_id=user_id, service=service)
    if not entry:
        return {"error": "password_not_found"}
    return entry


@router.get("/")
def adaptive_root():
    return RedirectResponse(url="/adaptive/status")

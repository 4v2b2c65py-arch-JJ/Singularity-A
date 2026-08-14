#!/usr/bin/env python3
"""
QB Protocol - Siri Integration API Routes
Full artificial Siri link with voice commands, Shortcuts, and sessions.
"""

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict

try:
    from qb_protocol.siri_integration.siri import siri_integration
    from qb_protocol.siri_integration.shortcuts import shortcut_manager
    from qb_protocol.siri_integration.session import siri_session_manager
    HAS_SIRI = True
except ImportError:
    try:
        from siri_integration.siri import siri_integration
        from siri_integration.shortcuts import shortcut_manager
        from siri_integration.session import siri_session_manager
        HAS_SIRI = True
    except ImportError:
        HAS_SIRI = False

router = APIRouter(prefix="/siri", tags=["siri"])


@router.get("/status")
def siri_status():
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    return siri_integration.get_status()


@router.post("/oauth/register")
def register_oauth(body: Dict[str, Any] = Body(...)):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    token = body.get("token", "")
    expires_in = int(body.get("expires_in", 3600))
    if not token:
        return {"error": "token_required"}
    return siri_integration.register_oauth_token(token=token, expires_in=expires_in)


@router.post("/session/create")
def create_session(body: Dict[str, Any] = Body(...)):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    user_id = body.get("user_id", "default")
    device_id = body.get("device_id", "unknown")
    platform = body.get("platform", "ios")
    scopes = body.get("scopes", ["chat", "execute", "control"])
    return siri_integration.create_session_token(user_id=user_id, device_id=device_id, platform=platform, scopes=scopes)


@router.post("/session/validate")
def validate_session(body: Dict[str, Any] = Body(...)):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    token = body.get("token", "")
    if not token:
        return {"error": "token_required"}
    session = siri_integration.validate_session_token(token)
    if not session:
        return {"error": "invalid_session"}
    return session


@router.post("/voice/command")
def voice_command(body: Dict[str, Any] = Body(...)):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    utterance = body.get("utterance", "")
    session_token = body.get("session_token", "")
    context = body.get("context", {})
    if not utterance or not session_token:
        return {"error": "utterance_and_session_token_required"}
    return siri_integration.process_voice_command(utterance=utterance, session_token=session_token, context=context)


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    session = siri_integration.get_session(session_id)
    if not session:
        return {"error": "session_not_found"}
    return session


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, limit: int = 100):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    messages = siri_integration.get_messages(session_id, limit=limit)
    return {"session_id": session_id, "messages": messages}


@router.post("/shortcuts")
def create_shortcut(body: Dict[str, Any] = Body(...)):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    name = body.get("name", "")
    intent = body.get("intent", "chat")
    action = body.get("action", "")
    siri_phrase = body.get("siri_phrase", "")
    parameters = body.get("parameters", {})
    if not name or not siri_phrase:
        return {"error": "name_and_siri_phrase_required"}
    shortcut = shortcut_manager.register_shortcut(name=name, intent=intent, action=action, siri_phrase=siri_phrase, parameters=parameters)
    return asdict(shortcut)


@router.get("/shortcuts")
def get_shortcuts():
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    return {"shortcuts": shortcut_manager.get_shortcuts()}


@router.get("/shortcuts/status")
def shortcuts_status():
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    return shortcut_manager.get_status()


@router.post("/session/context")
def update_session_context(body: Dict[str, Any] = Body(...)):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    session_id = body.get("session_id", "")
    context = body.get("context", {})
    if not session_id:
        return {"error": "session_id_required"}
    return siri_session_manager.update_context(session_id=session_id, context=context)


@router.get("/session/private/{user_id}")
def get_private_context(user_id: str):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    return siri_session_manager.get_private_context(user_id=user_id)


@router.post("/session/private")
def set_private_context(body: Dict[str, Any] = Body(...)):
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    user_id = body.get("user_id", "default")
    key = body.get("key", "")
    value = body.get("value", "")
    if not key:
        return {"error": "key_required"}
    return siri_session_manager.set_private_context(user_id=user_id, key=key, value=value)


@router.get("/sessions")
def get_sessions():
    if not HAS_SIRI:
        return {"error": "siri_unavailable"}
    with siri_session_manager._lock:
        return {"sessions": [asdict(s) for s in siri_session_manager.sessions.values()]}


@router.get("/")
def siri_root():
    return RedirectResponse(url="/siri/status")

#!/usr/bin/env python3
"""
QB Protocol - Telecom API Routes
"""

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.telecom.phone.validator import phone_validator
    from qb_protocol.telecom.sms.providers import sms_adapter, TelnyxProvider, VonageProvider, SinchProvider
    from qb_protocol.telecom.voice.webrtc import webrtc_manager
    from qb_protocol.telecom.otp.manager import otp_manager
    from qb_protocol.telecom.privacy.architecture import privacy_manager
    HAS_TELECOM = True
except ImportError:
    try:
        from telecom.phone.validator import phone_validator
        from telecom.sms.providers import sms_adapter, TelnyxProvider, VonageProvider, SinchProvider
        from telecom.voice.webrtc import webrtc_manager
        from telecom.otp.manager import otp_manager
        from telecom.privacy.architecture import privacy_manager
        HAS_TELECOM = True
    except ImportError:
        HAS_TELECOM = False

router = APIRouter(prefix="/telecom", tags=["telecom"])


@router.get("/status")
def telecom_status():
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return {
        "phone": phone_validator.get_status(),
        "sms": sms_adapter.get_status(),
        "voice": webrtc_manager.get_status(),
        "otp": otp_manager.get_status(),
        "privacy": privacy_manager.get_status(),
    }


@router.post("/phone/validate")
def validate_phone(body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    phone = body.get("phone", "")
    region = body.get("region")
    info = phone_validator.validate(phone, region)
    return info


@router.get("/phone/validated")
def get_validated_phones():
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return phone_validator.get_phones()


@router.post("/sms/send")
def send_sms(body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    message = sms_adapter.send_sms(
        to=body.get("to", ""),
        text=body.get("text", ""),
        provider_name=body.get("provider"),
        from_number=body.get("from_number"),
    )
    return message


@router.get("/sms/messages")
def get_sms_messages(limit: int = 100):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return sms_adapter.get_messages(limit)


@router.post("/sms/providers")
def register_sms_provider(body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    name = body.get("name", "")
    provider_type = body.get("type", "")
    if provider_type == "telnyx":
        provider = TelnyxProvider(
            api_key=body.get("api_key", ""),
            from_number=body.get("from_number", ""),
        )
    elif provider_type == "vonage":
        provider = VonageProvider(
            api_key=body.get("api_key", ""),
            api_secret=body.get("api_secret", ""),
            from_name=body.get("from_name", ""),
        )
    elif provider_type == "sinch":
        provider = SinchProvider(
            api_key=body.get("api_key", ""),
            api_secret=body.get("api_secret", ""),
            from_number=body.get("from_number", ""),
        )
    else:
        return {"error": "unsupported_provider_type"}
    sms_adapter.register_provider(name, provider)
    return {"status": "registered", "name": name, "type": provider_type}


@router.get("/sms/providers")
def get_sms_providers():
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return sms_adapter.get_status()


@router.post("/voice/sessions")
def create_voice_session(body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    session = webrtc_manager.create_session(
        caller_id=body.get("caller_id", ""),
        callee_id=body.get("callee_id", ""),
        turn_config=body.get("turn_config"),
    )
    return session


@router.post("/voice/sessions/{session_id}/status")
def update_voice_session(session_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    session = webrtc_manager.update_session_status(session_id, body.get("status", ""))
    return session if session else {"error": "session_not_found"}


@router.get("/voice/sessions")
def get_voice_sessions():
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return webrtc_manager.get_sessions()


@router.post("/otp/generate")
def generate_otp(body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    otp = otp_manager.generate(
        phone=body.get("phone", ""),
        ttl_seconds=body.get("ttl_seconds", 300),
        max_attempts=body.get("max_attempts", 3),
    )
    return otp


@router.post("/otp/verify")
def verify_otp(body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return otp_manager.verify(
        phone=body.get("phone", ""),
        code=body.get("code", ""),
    )


@router.get("/otp/codes")
def get_otp_codes(phone: Optional[str] = None):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return otp_manager.get_codes(phone)


@router.get("/privacy/config")
def get_privacy_config():
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    return privacy_manager.get_config()


@router.post("/privacy/config")
def update_privacy_config(body: Dict[str, Any] = Body(...)):
    if not HAS_TELECOM:
        return {"error": "telecom_unavailable"}
    config = privacy_manager.update_config(**body)
    return config

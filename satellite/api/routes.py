#!/usr/bin/env python3
"""
QB Protocol - Satellite API Routes
Real satellite/modem communication only. No simulation fallback.
"""

import uuid
from dataclasses import asdict
from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional

try:
    from qb_protocol.satellite.core.iridium import iridium_manager
    from qb_protocol.satellite.core.security import satellite_security
    from qb_protocol.satellite.core.government import government_assurance
    from qb_protocol.satellite.core.udp_bridge import udp_bridge
    HAS_SATELLITE = True
except ImportError:
    try:
        from satellite.core.iridium import iridium_manager
        from satellite.core.security import satellite_security
        from satellite.core.government import government_assurance
        from satellite.core.udp_bridge import udp_bridge
        HAS_SATELLITE = True
    except ImportError:
        HAS_SATELLITE = False

router = APIRouter(prefix="/satellite", tags=["satellite"])


@router.get("/status")
def satellite_status():
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    return {
        "iridium": iridium_manager.get_status(),
        "security": satellite_security.get_status(),
        "government": government_assurance.get_status(),
        "udp_bridge": {
            "host": udp_bridge.host,
            "port": udp_bridge.port,
            "running": udp_bridge._running,
        },
    }


@router.post("/modems")
def register_modem(body: Dict[str, Any] = Body(...)):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    from satellite.core.iridium import SatelliteConfig
    config = SatelliteConfig(
        port=body.get("port", "/dev/ttyUSB0"),
        baudrate=body.get("baudrate", 19200),
        timeout=body.get("timeout", 2.0),
        registration_timeout=body.get("registration_timeout", 180),
        max_payload_bytes=body.get("max_payload_bytes", 340),
        government_assured=body.get("government_assured", True),
    )
    modem_id = body.get("modem_id", str(uuid.uuid4()))
    modem = iridium_manager.register_modem(modem_id, config)
    return {"modem_id": modem_id, "config": asdict(config)}


@router.post("/modems/{modem_id}/check")
def check_modem(modem_id: str):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    from satellite.core.iridium import iridium_manager
    with iridium_manager._lock:
        modem = iridium_manager.modems.get(modem_id)
    if not modem:
        return {"error": "modem_not_found"}
    result = modem.check_modem()
    return result


@router.post("/modems/{modem_id}/signal")
def signal_quality(modem_id: str):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    from satellite.core.iridium import iridium_manager
    with iridium_manager._lock:
        modem = iridium_manager.modems.get(modem_id)
    if not modem:
        return {"error": "modem_not_found"}
    quality = modem.signal_quality()
    return {"modem_id": modem_id, "signal_quality": quality}


@router.post("/modems/{modem_id}/register")
def register_satellite(modem_id: str):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    from satellite.core.iridium import iridium_manager
    with iridium_manager._lock:
        modem = iridium_manager.modems.get(modem_id)
    if not modem:
        return {"error": "modem_not_found"}
    result = modem.wait_for_registration()
    return result


@router.post("/modems/{modem_id}/send")
def send_satellite_message(modem_id: str, body: Dict[str, Any] = Body(...)):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    payload = body.get("payload", b"")
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    result = iridium_manager.send_message(modem_id, payload)
    return result


@router.post("/modems/{modem_id}/receive")
def receive_satellite_message(modem_id: str):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    result = iridium_manager.receive_message(modem_id)
    return result


@router.get("/messages")
def get_satellite_messages(limit: int = 100):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    return iridium_manager.get_messages(limit)


@router.post("/security/authorize")
def authorize_security(body: Dict[str, Any] = Body(...)):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    security = satellite_security.authorize(
        clearance_level=body.get("clearance_level", "government"),
        encryption_key=body.get("encryption_key", ""),
        metadata=body.get("metadata"),
    )
    return security


@router.get("/security/{security_id}")
def get_security(security_id: str):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    return satellite_security.get_security(security_id)


@router.post("/government/approve")
def approve_compliance(body: Dict[str, Any] = Body(...)):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    assurance = government_assurance.approve(
        compliance_level=body.get("compliance_level", "government"),
        authority=body.get("authority", "QB Protocol"),
        certification_id=body.get("certification_id", ""),
        restrictions=body.get("restrictions"),
        metadata=body.get("metadata"),
    )
    return assurance


@router.post("/government/revoke/{assurance_id}")
def revoke_compliance(assurance_id: str):
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    result = government_assurance.revoke(assurance_id)
    return {"revoked": result}


@router.get("/government/assurances")
def get_assurances():
    if not HAS_SATELLITE:
        return {"error": "satellite_unavailable"}
    return government_assurance.get_status()

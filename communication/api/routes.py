#!/usr/bin/env python3
"""
QB Protocol - Communication API Routes
Peer discovery, live portals, celestial router, and geo-matching endpoints.
"""

import uuid
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Dict, Any, Optional
from dataclasses import asdict
from datetime import datetime

try:
    from qb_protocol.communication.celestial_router import celestial_router
    from qb_protocol.communication.coordinate_system import coordinate_system
    from qb_protocol.communication.peer_discovery import peer_discovery
    HAS_COMMUNICATION = True
except ImportError:
    try:
        from communication.celestial_router import celestial_router
        from communication.coordinate_system import coordinate_system
        from communication.peer_discovery import peer_discovery
        HAS_COMMUNICATION = True
    except ImportError:
        HAS_COMMUNICATION = False

router = APIRouter(prefix="/communication", tags=["communication"])


@router.get("/status")
def communication_status():
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return {
        "celestial_router": celestial_router.get_status(),
        "coordinates": coordinate_system.get_status(),
        "peer_discovery": peer_discovery.get_status(),
    }


@router.get("/dimensions")
def get_dimensions():
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return {"dimensions": celestial_router.get_dimensions()}


@router.get("/dimensions/{dimension_id}")
def get_dimension(dimension_id: str):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    dim = celestial_router.get_dimension(dimension_id)
    if not dim:
        return {"error": "dimension_not_found"}
    return dim


@router.post("/dimensions/register")
def register_dimension(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    name = body.get("name", "")
    coordinates = body.get("coordinates", {})
    universe = body.get("universe", "earth")
    stability = float(body.get("stability", 1.0))
    metadata = body.get("metadata", {})
    if not name or not coordinates:
        return {"error": "missing_required_fields"}
    dim = celestial_router.register_dimension(name, coordinates, universe, stability, metadata)
    return dim


@router.post("/dimensions/route")
def route_connection(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    source = body.get("source_dimension", "")
    target = body.get("target_dimension", "")
    if not source or not target:
        return {"error": "missing_dimensions"}
    return celestial_router.route_connection(source, target)


@router.get("/connections")
def get_connections():
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return {"connections": celestial_router.get_connections()}


@router.post("/coordinates")
def register_coordinate(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    name = body.get("name", "")
    latitude = float(body.get("latitude", 0))
    longitude = float(body.get("longitude", 0))
    altitude = body.get("altitude")
    dimension = body.get("dimension", "earth")
    metadata = body.get("metadata", {})
    if not name:
        return {"error": "name_required"}
    coord = coordinate_system.register(name, latitude, longitude, altitude, dimension, metadata)
    return asdict(coord)


@router.get("/coordinates")
def list_coordinates():
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return {"coordinates": coordinate_system.list_all()}


@router.post("/peers/discover/environment")
def discover_peers_environment(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    environment_type = body.get("environment_type", "")
    environment_id = body.get("environment_id", "")
    device_id = body.get("device_id", "")
    if not environment_type or not environment_id or not device_id:
        return {"error": "missing_required_fields"}
    peers = peer_discovery.discover_in_environment(environment_type, environment_id, device_id)
    return {"peers": peers, "count": len(peers)}


@router.post("/peers/discover/geo")
def discover_peers_geo(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    lat = float(body.get("lat", 0))
    lon = float(body.get("lon", 0))
    radius_km = float(body.get("radius_km", 50))
    device_id = body.get("device_id", "")
    peers = peer_discovery.discover_by_geo(lat, lon, radius_km, device_id)
    return {"peers": peers, "count": len(peers)}


@router.post("/peers/discover/btc-rank")
def discover_peers_btc_rank(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    environment_type = body.get("environment_type", "global")
    limit = int(body.get("limit", 50))
    device_id = body.get("device_id", "")
    peers = peer_discovery.discover_by_btc_rank(environment_type, limit, device_id)
    return {"peers": peers, "count": len(peers)}


@router.post("/peers/discover/linked")
def discover_peers_linked(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    dimension_id = body.get("dimension_id", "")
    device_id = body.get("device_id", "")
    if not dimension_id or not device_id:
        return {"error": "missing_required_fields"}
    peers = peer_discovery.discover_linked_environments(dimension_id, device_id)
    return {"peers": peers, "count": len(peers)}


@router.get("/portals/live")
def get_live_portals(device_id: str = ""):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    portals = peer_discovery.get_live_portals(device_id)
    return {"portals": portals, "count": len(portals)}


@router.post("/peers/register")
def register_peer(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    from communication.peer_discovery import PeerRecord
    try:
        peer = PeerRecord(
            peer_id=body.get("peer_id", str(uuid.uuid4())),
            user_id=body.get("user_id", ""),
            device_id=body.get("device_id", ""),
            environment_type=body.get("environment_type", ""),
            environment_id=body.get("environment_id", ""),
            dimension_id=body.get("dimension_id", ""),
            btc_public_address=body.get("btc_public_address", ""),
            geo=body.get("geo", {}),
            signal_strength=float(body.get("signal_strength", 0)),
            last_seen=datetime.utcnow().isoformat() + "Z",
            portal_url=body.get("portal_url"),
            metadata=body.get("metadata", {}),
        )
        peer_discovery.register_peer(peer)
        return {"registered": True, "peer_id": peer.peer_id}
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/")
def communication_root():
    return RedirectResponse(url="/communication/status")

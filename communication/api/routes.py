#!/usr/bin/env python3
"""
QB Protocol - Communication API Routes
Live discovery, registry dumps, peer matching, and geo endpoints.
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
    from qb_protocol.communication.peer_discovery import live_discovery
    HAS_COMMUNICATION = True
except ImportError:
    try:
        from communication.celestial_router import celestial_router
        from communication.coordinate_system import coordinate_system
        from communication.peer_discovery import live_discovery
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
        "peer_discovery": live_discovery.get_status(),
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
    return asdict(dim)


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


@router.get("/registry/dump")
def registry_dump(use_tor: bool = False):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return live_discovery.get_registry_dump(use_tor=use_tor)


@router.post("/discover")
def discover_peers(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    context = body.get("context", "general")
    use_tor = bool(body.get("use_tor", False))
    use_vpn = bool(body.get("use_vpn", False))
    return live_discovery.discover(context=context, use_tor=use_tor, use_vpn=use_vpn)


@router.post("/discover/geo")
def discover_geo(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    lat = float(body.get("lat", 0))
    lon = float(body.get("lon", 0))
    radius_km = float(body.get("radius_km", 50))
    use_tor = bool(body.get("use_tor", False))
    return live_discovery.discover_geo(lat, lon, radius_km, use_tor=use_tor)


@router.post("/discover/btc-rank")
def discover_btc_rank(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    environment_type = body.get("environment_type", "global")
    limit = int(body.get("limit", 50))
    use_tor = bool(body.get("use_tor", False))
    return live_discovery.discover_btc_rank(environment_type, limit, use_tor=use_tor)


@router.get("/endpoints")
def list_endpoints():
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return {
        "endpoints": [
            {
                "endpoint": ep.endpoint,
                "method": ep.method,
                "path": ep.path,
                "timeout": ep.timeout,
                "retries": ep.retries,
            }
            for ep in live_discovery._endpoints
        ]
    }


@router.post("/endpoints")
def add_endpoint(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    endpoint = body.get("endpoint", "local")
    method = body.get("method", "GET")
    path = body.get("path", "")
    timeout = float(body.get("timeout", 5.0))
    headers = body.get("headers", {})
    params = body.get("params", {})
    body_data = body.get("body", {})
    if not path:
        return {"error": "path_required"}
    live_discovery.add_endpoint(endpoint, method, path, timeout, headers, params, body_data)
    return {"added": True, "endpoint": endpoint, "path": path}


@router.get("/portals/live")
def get_live_portals(device_id: str = ""):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return live_discovery.discover(context="live portals", use_tor=False)


@router.post("/peers/register")
def register_peer(body: Dict[str, Any] = Body(...)):
    if not HAS_COMMUNICATION:
        return {"error": "communication_unavailable"}
    return {
        "registered": True,
        "peer_id": str(uuid.uuid4()),
        "message": "Live discovery does not persist peers. Use /communication/registry/dump for live state.",
    }


@router.get("/")
def communication_root():
    return RedirectResponse(url="/communication/status")

#!/usr/bin/env python3
"""
QB Protocol - Global API Gateway
Unified entry point for all device node service packages with signature enforcement.
"""

import os
import sys
import time
import uuid
import json
import logging
import hashlib
import hmac
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    from qb_protocol.core.daemon import daemon
    from qb_protocol.agent.entry_gate import entry_gate
    from qb_protocol.agent.guest_session import guest_session_manager
    from qb_protocol.ai.gpt_layer import gpt_layer
    from qb_protocol.package.node_service_package import node_package, rate_limiter
    from qb_protocol.server.api_server import (
        reality_stabilizer, dream_engine, healing_system, ip_geo
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon
    from agent.entry_gate import entry_gate
    from agent.guest_session import guest_session_manager
    from ai.gpt_layer import gpt_layer
    from package.node_service_package import node_package, rate_limiter
    from server.api_server import (
        reality_stabilizer, dream_engine, healing_system, ip_geo
    )

LOG = logging.getLogger("qb_protocol.gateway")
GATEWAY_SECRET = os.environ.get("QB_GATEWAY_SECRET", "qb-global-gateway-secret")
try:
    from ai.gpt_layer import gpt_layer
    HAS_AI = True
except ImportError:
    HAS_AI = False
app = FastAPI(title="QB Protocol Global Gateway", version="1.0.0")


class EntryAuth(BaseModel):
    entry_code: str
    signature: str
    agent_id: Optional[str] = None


class InstanceCreate(BaseModel):
    name: str
    platform: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    entry: Optional[EntryAuth] = None


class DreamLayerCreate(BaseModel):
    depth: float
    projection: Dict[str, Any]
    convergence: float = 0.0
    brain_state_emission: float = 0.0
    singularity_threshold: float = 0.0
    entry: Optional[EntryAuth] = None


def _sign(payload: str) -> str:
    return hmac.new(GATEWAY_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def require_entry(entry: Optional[EntryAuth]) -> Dict[str, Any]:
    if not entry:
        raise HTTPException(status_code=401, detail="entry_required")
    result = entry_gate.validate_entry(entry.entry_code, entry.signature, entry.agent_id)
    if not result.get("valid"):
        raise HTTPException(status_code=403, detail=result.get("reason", "invalid_entry"))
    return result


@app.post("/entry/issue")
def issue_entry(agent_id: str, ttl_seconds: int = 3600):
    cred = entry_gate.issue_entry(agent_id, ttl_seconds)
    return {"status": "ok", "entry_code": cred.entry_code, "signature": cred.signature, "expires_at": cred.expires_at}


@app.post("/entry/validate")
def validate_entry(entry: EntryAuth):
    result = require_entry(entry)
    return {"status": "ok", "valid": True, "agent_id": result.get("agent_id")}


@app.get("/status")
def global_status():
    return {
        "gateway": "active",
        "node_id": daemon.node_id,
        "daemon": daemon.get_status(),
        "healing": healing_system.get_status(),
        "stabilizer": reality_stabilizer.get_status(),
        "dream": dream_engine.get_status(),
    }


@app.post("/instances")
def create_instance(body: InstanceCreate):
    if body.entry:
        require_entry(body.entry)
    else:
        if not rate_limiter.allow("instances"):
            raise HTTPException(status_code=429, detail="rate_limited")
    inst = daemon.register_instance(body.name, body.platform, body.metadata)
    return {"status": "ok", "instance_id": inst.instance_id}


@app.post("/dream/layers")
def create_dream_layer(body: DreamLayerCreate):
    if body.entry:
        require_entry(body.entry)
    else:
        if not rate_limiter.allow("dream_engine"):
            raise HTTPException(status_code=429, detail="rate_limited")
    layer = daemon.add_dream_layer(body.depth, body.projection, body.convergence, body.brain_state_emission, body.singularity_threshold)
    return {"status": "ok", "layer_id": layer.layer_id}


@app.post("/ip/quick-connect")
def gateway_quick_ip():
    return ip_geo.quick_connect()


@app.get("/health")
def health():
    return {"status": "ok", "node_id": daemon.node_id, "platform": "Darwin"}


@app.post("/healing/regen")
def trigger_regen():
    healing_system.run_regen_cycle()
    return {"status": "ok", "regen_cycles": healing_system.regen_cycles}


@app.get("/brain/status")
def brain_status():
    try:
        from qb_protocol.vemex.mesh_brain import mesh_brain_reader
        return mesh_brain_reader.get_status()
    except ImportError:
        return {"error": "vemex_not_available"}


@app.get("/brain/read")
def brain_read():
    try:
        from qb_protocol.vemex.mesh_brain import mesh_brain_reader
        reading = mesh_brain_reader.read_brain_state()
        return asdict(reading)
    except ImportError:
        return {"error": "vemex_not_available"}


@app.post("/brain/query")
def brain_query(request: Request):
    body = request.query_params
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt_required")
    try:
        from qb_protocol.vemex.mesh_brain import mesh_brain_reader
        result = mesh_brain_reader.query_consciousness(prompt)
        return result
    except ImportError:
        return {"error": "vemex_not_available"}


@app.get("/uptime")
def uptime():
    return {"uptime_seconds": daemon.get_uptime(), "node_id": daemon.node_id}


@app.get("/oracle/status")
def oracle_status():
    try:
        from qb_protocol.oracle.tablet_oracle import tablet_oracle
        return tablet_oracle.get_status()
    except ImportError:
        return {"error": "oracle_not_available"}


@app.post("/oracle/consciousness")
def oracle_consciousness(request: Request):
    body = request.query_params
    prompt = body.get("prompt", "")
    max_iterations = int(body.get("max_iterations", "10"))
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt_required")
    try:
        from qb_protocol.oracle.tablet_oracle import tablet_oracle
        result = tablet_oracle.query_consciousness(prompt, max_iterations=max_iterations)
        return result
    except ImportError:
        return {"error": "oracle_not_available"}


@app.post("/oracle/magi-zone")
def oracle_magi_zone(request: Request):
    body = request.query_params
    voice_phrases = body.get("voice_phrases", "").split(",")
    origin3d = [float(x) for x in body.get("origin3d", "0,0,0").split(",")]
    movement_vector = [float(x) for x in body.get("movement_vector", "1,0,0").split(",")]
    in_danger = body.get("in_danger", "true").lower() == "true"
    default_tier = int(body.get("default_tier", "2"))
    try:
        from qb_protocol.oracle.tablet_oracle import tablet_oracle
        result = tablet_oracle.run_magi_zone(voice_phrases, origin3d, movement_vector, in_danger, default_tier)
        return result
    except ImportError:
        return {"error": "oracle_not_available"}


@app.get("/oracle/brain-mesh")
def oracle_brain_mesh():
    try:
        from qb_protocol.oracle.tablet_oracle import tablet_oracle
        return tablet_oracle.read_brain_mesh()
    except ImportError:
        return {"error": "oracle_not_available"}


class GuestSessionIssue(BaseModel):
    agent_id: Optional[str] = None
    ttl_seconds: int = 3600
    permissions: Optional[List[str]] = None
    remote_server: Optional[str] = None


class GuestSessionAuth(BaseModel):
    session_id: str
    token: str


@app.post("/guest/issue")
def guest_issue(body: GuestSessionIssue):
    session = guest_session_manager.issue_session(
        agent_id=body.agent_id,
        ttl_seconds=body.ttl_seconds,
        permissions=body.permissions,
        remote_server=body.remote_server,
    )
    return {
        "status": "ok",
        "session_id": session.session_id,
        "token": session.token,
        "permissions": session.permissions,
        "expires_at": session.expires_at,
    }


@app.post("/guest/validate")
def guest_validate(body: GuestSessionAuth):
    result = guest_session_manager.validate_session(body.session_id, body.token)
    return {"status": "ok", **result}


@app.post("/guest/heartbeat")
def guest_heartbeat(body: GuestSessionAuth, remote_server: Optional[str] = None):
    result = guest_session_manager.heartbeat(body.session_id, body.token, remote_server=remote_server)
    return {"status": "ok", **result}


@app.get("/guest/env")
def guest_env(session_id: str, token: str):
    result = guest_session_manager.get_full_env(session_id, token)
    return result


@app.get("/guest/status")
def guest_status():
    return guest_session_manager.get_status()


@app.delete("/guest/revoke")
def guest_revoke(session_id: str, token: str):
    ok = guest_session_manager.revoke_session(session_id)
    return {"status": "ok" if ok else "not_found", "revoked": ok}


class AIQueryRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7


@app.get("/ai/status")
def ai_status():
    if not HAS_AI:
        return {"error": "ai_mode_unavailable"}
    return gpt_layer.get_status()


@app.post("/ai/query")
def ai_query(body: AIQueryRequest):
    if not HAS_AI:
        return {"error": "ai_mode_unavailable"}
    if not body.prompt:
        raise HTTPException(status_code=400, detail="prompt_required")
    return gpt_layer.query(body.prompt, max_tokens=body.max_tokens, temperature=body.temperature)


@app.get("/ai/history")
def ai_history(limit: int = 100):
    if not HAS_AI:
        return {"error": "ai_mode_unavailable"}
    return {"queries": gpt_layer.get_query_history(limit=limit)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=17761)

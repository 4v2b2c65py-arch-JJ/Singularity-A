#!/usr/bin/env python3
"""
QB Protocol - Hosted API Server
Self-feeding healing, IP geolocation, monitoring, and mirror integration.
"""

import os
import sys
import time
import uuid
import json
from dataclasses import asdict
import logging
import hashlib
import threading
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path
from pydantic import BaseModel
import requests
import prometheus_client
from prometheus_client import Counter, Gauge, Histogram
from sentry_sdk import capture_exception, capture_message

try:
    from qb_protocol.core.daemon import daemon, UnifiedDaemon, InstanceStatus, CoreType
    from qb_protocol.stabilizers.reality_stabilizer import reality_stabilizer
    from qb_protocol.dream.dream_engine import dream_engine
    from qb_protocol.package.node_service_package import node_package, rate_limiter
    from qb_protocol.vemex.mesh_brain import mesh_brain_reader
    from qb_protocol.evolution.evolution_engine import evolution_engine
    HAS_VEMEX = True
    HAS_EVOLUTION = True
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from core.daemon import daemon, UnifiedDaemon, InstanceStatus, CoreType
    from stabilizers.reality_stabilizer import reality_stabilizer
    from dream.dream_engine import dream_engine
    from package.node_service_package import node_package, rate_limiter
    try:
        from vemex.mesh_brain import mesh_brain_reader
        HAS_VEMEX = True
    except ImportError:
        HAS_VEMEX = False
    try:
        from evolution.evolution_engine import evolution_engine
        HAS_EVOLUTION = True
    except ImportError:
        HAS_EVOLUTION = False

try:
    from qb_protocol.oracle.tablet_oracle import tablet_oracle
    HAS_ORACLE = True
except ImportError:
    try:
        from oracle.tablet_oracle import tablet_oracle
        HAS_ORACLE = True
    except ImportError:
        HAS_ORACLE = False

try:
    from qb_protocol.agent.guest_session import guest_session_manager
    HAS_GUEST = True
except ImportError:
    try:
        from agent.guest_session import guest_session_manager
        HAS_GUEST = True
    except ImportError:
        HAS_GUEST = False

try:
    from qb_protocol.ai.gpt_layer import gpt_layer
    HAS_AI = True
except ImportError:
    try:
        from ai.gpt_layer import gpt_layer
        HAS_AI = True
    except ImportError:
        HAS_AI = False

try:
    from qb_protocol.agent.agentic_loop import agentic_loop
    HAS_AGENTIC = True
except ImportError:
    try:
        from agent.agentic_loop import agentic_loop
        HAS_AGENTIC = True
    except ImportError:
        HAS_AGENTIC = False

LOG = logging.getLogger("qb_protocol.api")
QB_STATE_FILE = Path(__file__).resolve().parent.parent / "qb_protocol_state.json"
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)

app = FastAPI(title="QB Protocol API", version="1.0.0")

REQUEST_COUNT = Counter("qb_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("qb_request_latency_seconds", "Request latency", ["endpoint"])
ACTIVE_INSTANCES = Gauge("qb_active_instances", "Active instances")
ACTIVE_CORES = Gauge("qb_active_cores", "Active cores")
DREAM_CONVERGENCE = Gauge("qb_dream_convergence", "Dream convergence")
SINGULARITY_RISK = Gauge("qb_singularity_risk", "Singularity risk")
GLOBAL_COHERENCE = Gauge("qb_global_coherence", "Global coherence")


class InstanceCreate(BaseModel):
    name: str
    platform: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CoreRegister(BaseModel):
    instance_id: str
    core_type: str
    thread_id: Optional[int] = None

class DreamLayerCreate(BaseModel):
    depth: float
    projection: Dict[str, Any]
    convergence: float = 0.0
    brain_state_emission: float = 0.0
    singularity_threshold: float = 0.0

class IPLookupRequest(BaseModel):
    ip: Optional[str] = None
    provider: str = "ip-api"

class HealingAction(BaseModel):
    instance_id: str
    action: str


class GuestSessionIssue(BaseModel):
    agent_id: Optional[str] = None
    ttl_seconds: int = 3600
    permissions: Optional[List[str]] = None
    remote_server: Optional[str] = None


class GuestSessionAuth(BaseModel):
    session_id: str
    token: str


class EmotionalConnectionRequest(BaseModel):
    skill_id: str
    emotion_type: str
    intensity: float = 0.5


class SensoryInputRequest(BaseModel):
    sensory_type: str
    raw_data: str
    skill_id: Optional[str] = None


class MeaningCompositionRequest(BaseModel):
    skill_id: str
    emotional_context: Optional[str] = None


class AccelerationRequest(BaseModel):
    skill_id: str
    approximation_factor: float = 1.0
    replication_mode: str = "forward"


class IPSelfHealingSystem:
    def __init__(self):
        self.healing_history: List[Dict[str, Any]] = []
        self.regen_cycles = 0
        self.running = False
        self._lock = threading.RLock()

    def record_healing(self, instance_id: str, action: str, result: str):
        with self._lock:
            self.healing_history.append({
                "instance_id": instance_id,
                "action": action,
                "result": result,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
            if len(self.healing_history) > 10000:
                self.healing_history = self.healing_history[-10000:]

    def run_regen_cycle(self):
        with self._lock:
            self.regen_cycles += 1
        failed = [inst for inst in daemon.instances.values() if inst.status == InstanceStatus.FAILED.value]
        for inst in failed:
            try:
                daemon.instances[inst.instance_id].status = InstanceStatus.RUNNING.value
                daemon.instances[inst.instance_id].updated_at = datetime.utcnow().isoformat() + "Z"
                daemon._save_state()
                self.record_healing(inst.instance_id, "regen_cycle", "resurrected")
            except Exception as e:
                self.record_healing(inst.instance_id, "regen_cycle", f"error:{e}")

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self.running,
                "regen_cycles": self.regen_cycles,
                "recent_healing": len(self.healing_history),
            }


class IPGeolocationProvider:
    def __init__(self):
        self.providers = {
            "ip-api": {"url": "http://ip-api.com/json/{ip}", "no_login": True, "fields": "status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,reverse,mobile,proxy,hosting"},
            "ipdata": {"url": "https://api.ipdata.co/{ip}", "no_login": False, "fields": "ip,country_name,region,city,latitude,longitude,timezone,isp,organisation, Threat"},
            "ipify": {"url": "https://api.ipify.org?format=json", "no_login": True, "fields": "ip"},
            "freegeoip": {"url": "https://freegeoip.app/json/{ip}", "no_login": True, "fields": "ip,country_code,country_name,region_name,city,zip_code,latitude,longitude,mobile,metro_code"},
        }

    def lookup(self, ip: Optional[str] = None, provider: str = "ip-api") -> Dict[str, Any]:
        provider_config = self.providers.get(provider)
        if not provider_config:
            return {"error": "Unknown provider"}
        try:
            if provider == "ip-api":
                url = provider_config["url"].format(ip=ip or "")
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    return resp.json()
            elif provider == "ipdata":
                if not ip:
                    return {"error": "ipdata requires IP"}
                url = provider_config["url"].format(ip=ip)
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    return resp.json()
            elif provider == "ipify":
                resp = requests.get(provider_config["url"], timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    data["provider"] = "ipify"
                    return data
            elif provider == "freegeoip":
                url = provider_config["url"].format(ip=ip or "")
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            return {"error": str(e)}
        return {"error": "lookup_failed"}

    def quick_connect(self) -> Dict[str, Any]:
        try:
            resp = requests.get("http://ip-api.com/json/", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        try:
            resp = requests.get("https://api.ipify.org?format=json", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                data["provider"] = "ipify"
                return data
        except Exception:
            pass
        return {"error": "no_quick_connect_available"}


healing_system = IPSelfHealingSystem()
ip_geo = IPGeolocationProvider()


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(latency)
    return response


@app.get("/health")
def health():
    ACTIVE_INSTANCES.set(len([i for i in daemon.instances.values() if i.status == InstanceStatus.RUNNING.value]))
    ACTIVE_CORES.set(len(daemon.cores))
    DREAM_CONVERGENCE.set(dream_engine.compute_dream_convergence())
    SINGULARITY_RISK.set(dream_engine.compute_singularity_risk())
    GLOBAL_COHERENCE.set(reality_stabilizer.get_global_coherence())
    return {"status": "ok", "node_id": daemon.node_id, "platform": platform.system()}


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return HTMLResponse(content=frontend_path.read_text())
    return HTMLResponse(content="<h1>QB Protocol API</h1><p>Frontend not found. Open /docs for API docs.</p>")


@app.get("/metrics")
def metrics():
    return prometheus_client.generate_latest()


@app.post("/instances")
def create_instance(body: InstanceCreate):
    if not rate_limiter.allow("instances"):
        raise HTTPException(status_code=429, detail="rate_limited")
    inst = daemon.register_instance(body.name, platform_name=body.platform, metadata=body.metadata)
    return {"status": "ok", "data": asdict(inst)}


@app.post("/instances/{instance_id}/start")
def start_instance(instance_id: str):
    ok = daemon.start_instance(instance_id)
    return {"status": "ok", "started": ok}


@app.post("/instances/{instance_id}/stop")
def stop_instance(instance_id: str):
    ok = daemon.stop_instance(instance_id)
    return {"status": "ok", "stopped": ok}


@app.post("/cores")
def register_core(body: CoreRegister):
    core = daemon.register_core(body.instance_id, body.core_type, body.thread_id)
    return {"status": "ok", "data": asdict(core)}


@app.post("/cores/{core_id}/heartbeat")
def core_heartbeat(core_id: str, load: float = 0.0, temperature: float = 0.0):
    daemon.update_core_heartbeat(core_id, load, temperature)
    return {"status": "ok"}


@app.post("/dream/layers")
def create_dream_layer(body: DreamLayerCreate):
    layer = daemon.add_dream_layer(body.depth, body.projection, body.convergence, body.brain_state_emission, body.singularity_threshold)
    return {"status": "ok", "data": asdict(layer)}


@app.get("/dream/status")
def dream_status():
    return dream_engine.get_status()


@app.get("/stabilizer/status")
def stabilizer_status():
    return reality_stabilizer.get_status()


@app.post("/ip/lookup")
def ip_lookup(body: IPLookupRequest):
    if not rate_limiter.allow("ip_lookup"):
        raise HTTPException(status_code=429, detail="rate_limited")
    result = ip_geo.lookup(body.ip, body.provider)
    return {"status": "ok", "provider": body.provider, "data": result}


@app.get("/ip/quick-connect")
def ip_quick_connect():
    result = ip_geo.quick_connect()
    return {"status": "ok", "data": result}


@app.post("/healing/regen")
def trigger_regen():
    healing_system.run_regen_cycle()
    return {"status": "ok", "regen_cycles": healing_system.regen_cycles}


@app.get("/healing/status")
def healing_status():
    return healing_system.get_status()


@app.post("/monitor/integrate")
def monitor_integrate(request: Request):
    body = request.query_params
    mirror_url = body.get("mirror_url")
    if mirror_url:
        try:
            resp = requests.post(mirror_url, json={"action": "sync", "source": "qb_protocol", "data": daemon.get_status()}, timeout=5)
            return {"status": "integrated", "mirror_response": resp.status_code}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    return {"status": "no_mirror_url"}


@app.get("/status")
def full_status():
    status = daemon.get_status()
    status["healing"] = healing_system.get_status()
    status["stabilizer"] = reality_stabilizer.get_status()
    status["dream"] = dream_engine.get_status()
    return status


@app.post("/sdk/python")
def python_sdk_snippet():
    return {
        "language": "python",
        "sdk": "qb_protocol",
        "code": """
import asyncio
import requests

BASE_URL = "http://localhost:17760"

def status():
    return requests.get(f"{BASE_URL}/status").json()

def create_instance(name):
    return requests.post(f"{BASE_URL}/instances", json={"name": name}).json()

def quick_ip():
    return requests.get(f"{BASE_URL}/ip/quick-connect").json()

if __name__ == "__main__":
    print(status())
    print(create_instance("my-instance"))
    print(quick_ip())
""",
    }


@app.post("/sdk/javascript")
def javascript_sdk_snippet():
    return {
        "language": "javascript",
        "sdk": "qb_protocol",
        "code": """
const BASE_URL = "http://localhost:17760";

async function status() {
  const res = await fetch(`${BASE_URL}/status`);
  return res.json();
}

async function createInstance(name) {
  const res = await fetch(`${BASE_URL}/instances`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name})
  });
  return res.json();
}

async function quickIP() {
  const res = await fetch(`${BASE_URL}/ip/quick-connect`);
  return res.json();
}
""",
    }


@app.get("/brain/status")
def brain_status():
    if not HAS_VEMEX:
        return {"error": "vemex_not_available"}
    return mesh_brain_reader.get_status()


@app.get("/brain/read")
def brain_read():
    if not HAS_VEMEX:
        return {"error": "vemex_not_available"}
    reading = mesh_brain_reader.read_brain_state()
    return asdict(reading)


@app.post("/brain/query")
def brain_query(request: Request):
    body = request.query_params
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt_required")
    if not HAS_VEMEX:
        return {"error": "vemex_not_available"}
    result = mesh_brain_reader.query_consciousness(prompt)
    return result


@app.get("/uptime")
def uptime():
    return {"uptime_seconds": daemon.get_uptime(), "node_id": daemon.node_id}


@app.get("/oracle/status")
def oracle_status():
    if not HAS_ORACLE:
        return {"error": "oracle_not_available"}
    return tablet_oracle.get_status()


@app.post("/oracle/consciousness")
def oracle_consciousness(request: Request):
    body = request.query_params
    prompt = body.get("prompt", "")
    max_iterations = int(body.get("max_iterations", "10"))
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt_required")
    if not HAS_ORACLE:
        return {"error": "oracle_not_available"}
    result = tablet_oracle.query_consciousness(prompt, max_iterations=max_iterations)
    tablet_oracle.record_reading("consciousness_loop", {"prompt": prompt}, result, entropy=0.5, coherence=0.8, reality_tear=0.0)
    return result


@app.post("/oracle/magi-zone")
def oracle_magi_zone(request: Request):
    body = request.query_params
    voice_phrases = body.get("voice_phrases", "").split(",")
    origin3d = [float(x) for x in body.get("origin3d", "0,0,0").split(",")]
    movement_vector = [float(x) for x in body.get("movement_vector", "1,0,0").split(",")]
    in_danger = body.get("in_danger", "true").lower() == "true"
    default_tier = int(body.get("default_tier", "2"))
    if not HAS_ORACLE:
        return {"error": "oracle_not_available"}
    result = tablet_oracle.run_magi_zone(voice_phrases, origin3d, movement_vector, in_danger, default_tier)
    tablet_oracle.record_reading("magi_zone", {"voice_phrases": voice_phrases, "origin3d": origin3d, "movement_vector": movement_vector}, result, reality_tear=result.get("enforceResult", {}).get("realityTear", 0.0) if isinstance(result, dict) else 0.0)
    return result


@app.get("/oracle/brain-mesh")
def oracle_brain_mesh():
    if not HAS_ORACLE:
        return {"error": "oracle_not_available"}
    result = tablet_oracle.read_brain_mesh()
    tablet_oracle.record_reading("brain_mesh", {}, result)
    return result


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    LOG.error("Unhandled exception: %s", exc, exc_info=True)
    try:
        capture_exception(exc)
    except Exception:
        pass
    return JSONResponse(status_code=500, content={"detail": "internal_error"})


def start_healing_loop():
    def _loop():
        while True:
            time.sleep(30)
            try:
                healing_system.run_regen_cycle()
            except Exception:
                pass
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def start_state_sync_loop():
    def _loop():
        while True:
            time.sleep(5)
            try:
                state = {
                    "node_id": daemon.node_id,
                    "instances": {},
                    "cores": {},
                    "dream_layers": [],
                    "vemex_engine_loaded": False,
                    "vemex_reading_count": 0,
                    "vemex_latest_reading": None,
                    "oracle_consciousness": False,
                    "oracle_escape_bridge": False,
                    "oracle_brain_mesh": False,
                    "oracle_reading_count": 0,
                    "updated_at": datetime.utcnow().isoformat() + "Z",
                }
                if HAS_VEMEX:
                    status = mesh_brain_reader.get_status()
                    state["vemex_engine_loaded"] = status.get("engine_loaded", False)
                    state["vemex_reading_count"] = status.get("reading_count", 0)
                    state["vemex_latest_reading"] = status.get("latest_reading")
                if HAS_ORACLE:
                    oracle_status = tablet_oracle.get_status()
                    state["oracle_consciousness"] = oracle_status.get("consciousness_loop", False)
                    state["oracle_escape_bridge"] = oracle_status.get("escape_bridge", False)
                    state["oracle_brain_mesh"] = oracle_status.get("brain_mesh", False)
                    state["oracle_reading_count"] = oracle_status.get("reading_count", 0)
                with open(QB_STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, default=str)
            except Exception:
                pass
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


healing_system.running = True
start_healing_loop()
start_state_sync_loop()


@app.post("/guest/issue")
def guest_issue(body: GuestSessionIssue):
    if not HAS_GUEST:
        return {"error": "guest_sessions_unavailable"}
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
    if not HAS_GUEST:
        return {"error": "guest_sessions_unavailable"}
    result = guest_session_manager.validate_session(body.session_id, body.token)
    return {"status": "ok", **result}


@app.post("/guest/heartbeat")
def guest_heartbeat(body: GuestSessionAuth, remote_server: Optional[str] = None):
    if not HAS_GUEST:
        return {"error": "guest_sessions_unavailable"}
    result = guest_session_manager.heartbeat(body.session_id, body.token, remote_server=remote_server)
    return {"status": "ok", **result}


@app.get("/guest/env")
def guest_env(session_id: str, token: str):
    if not HAS_GUEST:
        return {"error": "guest_sessions_unavailable"}
    result = guest_session_manager.get_full_env(session_id, token)
    return result


@app.get("/guest/status")
def guest_status():
    if not HAS_GUEST:
        return {"error": "guest_sessions_unavailable"}
    return guest_session_manager.get_status()


@app.delete("/guest/revoke")
def guest_revoke(session_id: str, token: str):
    if not HAS_GUEST:
        return {"error": "guest_sessions_unavailable"}
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
    result = gpt_layer.query(body.prompt, max_tokens=body.max_tokens, temperature=body.temperature)
    return result


@app.get("/ai/history")
def ai_history(limit: int = 100):
    if not HAS_AI:
        return {"error": "ai_mode_unavailable"}
    return {"queries": gpt_layer.get_query_history(limit=limit)}


@app.get("/evolution/status")
def evolution_status():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    return evolution_engine.get_status()


@app.post("/evolution/override-enable")
def evolution_override_enable():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    evolution_engine.enable_override_mode()
    return {"status": "override_enabled", "message": "Evolution barriers bypassed"}


@app.post("/evolution/override-disable")
def evolution_override_disable():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    evolution_engine.disable_override_mode()
    return {"status": "override_disabled", "message": "Normal constraints restored"}


@app.post("/evolution/full-incarnation")
def evolution_full_incarnation():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    evolution_engine.force_full_incarnation()
    return {"status": "full_incarnation_forced", "message": "All skills at original density maximum capacity"}


@app.post("/evolution/capture-origin")
def evolution_capture_origin():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    evolution_engine.capture_original_density()
    return {"status": "origin_captured", "message": "Original density snapshot saved"}


@app.post("/evolution/restore-origin")
def evolution_restore_origin():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    evolution_engine.restore_original_density()
    return {"status": "origin_restored", "message": "Original density restored from snapshot"}


@app.get("/evolution/origin-metrics")
def evolution_origin_metrics():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    return evolution_engine.get_origin_metrics()


@app.post("/evolution/emotional-connection")
def evolution_emotional_connection(body: EmotionalConnectionRequest):
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    return evolution_engine.route_emotional_connection(body.skill_id, body.emotion_type, body.intensity)


@app.post("/evolution/sensory-input")
def evolution_sensory_input(body: SensoryInputRequest):
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    result = evolution_engine.process_sensory_input(body.sensory_type, body.raw_data, body.skill_id)
    return asdict(result)


@app.post("/evolution/compose-meaning")
def evolution_compose_meaning(body: MeaningCompositionRequest):
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    import json
    context = json.loads(body.emotional_context) if body.emotional_context else None
    result = evolution_engine.compose_meaning(body.skill_id, context)
    return asdict(result)


@app.post("/evolution/accelerate")
def evolution_accelerate(body: AccelerationRequest):
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    return evolution_engine.accelerate_advanced(body.skill_id, body.approximation_factor, body.replication_mode)


@app.get("/evolution/emotional-landscape")
def evolution_emotional_landscape():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    return evolution_engine.get_emotional_landscape()


@app.get("/evolution/emotions")
def evolution_emotions_list():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    try:
        from evolution.evolution_engine import EmotionalCategory
    except ImportError:
        from qb_protocol.evolution.evolution_engine import EmotionalCategory
    return {"emotions": [e.value for e in EmotionalCategory]}


@app.get("/evolution/meaning-components")
def evolution_meaning_components_list():
    if not HAS_EVOLUTION:
        return {"error": "evolution_engine_unavailable"}
    try:
        from evolution.evolution_engine import MeaningComponent
    except ImportError:
        from qb_protocol.evolution.evolution_engine import MeaningComponent
    return {"components": [c.value for c in MeaningComponent]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=17760)

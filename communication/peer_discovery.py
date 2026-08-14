#!/usr/bin/env python3
"""
QB Protocol - Peer Discovery
Passive auto-discovery from live endpoints. No manual registration.
Machine recognizes its own known instances and avoids self-reference.
"""

import os
import sys
import time
import uuid
import json
import math
import logging
import threading
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

LOG = logging.getLogger("qb_protocol.peer_discovery")

GEO_TOLERANCE_KM = 50.0
SIGNAL_MATCH_THRESHOLD = 0.7
TOR_SOCKS_HOST = os.environ.get("TOR_SOCKS_HOST", "127.0.0.1")
TOR_SOCKS_PORT = int(os.environ.get("TOR_SOCKS_PORT", "9050"))
VPN_INTERFACE = os.environ.get("VPN_INTERFACE", "utun")

DISCOVERY_STATE_PATH = Path.home() / ".qb_protocol_discovery_state.json"
MAX_DISCOVERY_DEPTH = int(os.environ.get("QB_MAX_DISCOVERY_DEPTH", "3"))
DISCOVERY_COOLDOWN_SECONDS = int(os.environ.get("QB_DISCOVERY_COOLDOWN", "300"))
MAX_ACTIVE_SESSIONS = int(os.environ.get("QB_MAX_ACTIVE_SESSIONS", "10"))


@dataclass
class EndpointProbe:
    endpoint: str
    method: str
    path: str
    timeout: float = 5.0
    retries: int = 2
    headers: Dict[str, str] = None
    params: Dict[str, Any] = None
    body: Dict[str, Any] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.params is None:
            self.params = {}
        if self.body is None:
            self.body = {}


@dataclass
class DiscoverySession:
    session_id: str
    dimension_id: str
    depth: int
    started_at: str
    last_probe_at: str
    probes_completed: List[str]
    peers_found: List[Dict[str, Any]]
    status: str
    ttl_seconds: int
    metadata: Dict[str, Any]
    offloaded: bool = False
    offload_location: Optional[str] = None


class LiveDiscovery:
    """Passive auto-discovery from live endpoints. No manual registration."""

    def __init__(self):
        self._lock = threading.Lock()
        self._endpoints: List[EndpointProbe] = []
        self._agent = None
        self._gpt_layer = None
        self._tor_router = None
        self._sessions: Dict[str, DiscoverySession] = {}
        self._dimension_exploration: Dict[str, Dict[str, Any]] = {}
        self._known_instances: Dict[str, Dict[str, Any]] = {}
        self._register_default_endpoints()
        self._load_state()

    def _load_state(self):
        if DISCOVERY_STATE_PATH.exists():
            try:
                with open(DISCOVERY_STATE_PATH, "r") as f:
                    data = json.load(f)
                for s in data.get("sessions", []):
                    self._sessions[s["session_id"]] = DiscoverySession(**s)
                self._dimension_exploration = data.get("dimension_exploration", {})
                self._known_instances = data.get("known_instances", {})
                LOG.info("Loaded discovery state: %d sessions, %d dimensions, %d known instances",
                         len(self._sessions), len(self._dimension_exploration), len(self._known_instances))
            except Exception as exc:
                LOG.warning("Failed to load discovery state: %s", exc)

    def _save_state(self):
        try:
            with open(DISCOVERY_STATE_PATH, "w") as f:
                json.dump({
                    "sessions": [asdict(s) for s in self._sessions.values()],
                    "dimension_exploration": self._dimension_exploration,
                    "known_instances": self._known_instances,
                }, f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save discovery state: %s", exc)

    def _register_default_endpoints(self):
        self._endpoints = [
            EndpointProbe(endpoint="local", method="GET", path="/communication/dimensions", timeout=5.0, retries=2),
            EndpointProbe(endpoint="local", method="GET", path="/communication/coordinates", timeout=5.0, retries=2),
            EndpointProbe(endpoint="local", method="GET", path="/mesh-rewards/multiverse/leaderboard", timeout=5.0, retries=2),
            EndpointProbe(endpoint="local", method="GET", path="/mesh-rewards/celestial/router/assignments", timeout=5.0, retries=2),
            EndpointProbe(endpoint="local", method="GET", path="/mesh-rewards/rewards/leaderboard", timeout=5.0, retries=2),
        ]
        try:
            self._auto_discover_endpoints()
        except Exception as exc:
            LOG.warning("Auto-discovery of endpoints failed: %s", exc)

    def _auto_discover_endpoints(self):
        """Auto-discover endpoints from system index rather than presets."""
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:17760/openapi.json", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                spec = json.loads(resp.read().decode("utf-8"))
            
            paths = spec.get("paths", {})
            discovered = []
            for path, methods in paths.items():
                if isinstance(methods, dict):
                    for method in methods.keys():
                        if method.upper() in ("GET", "POST"):
                            discovered.append(EndpointProbe(
                                endpoint="local",
                                method=method.upper(),
                                path=path,
                                timeout=5.0,
                                retries=2,
                            ))
            
            if discovered:
                self._endpoints = discovered
                LOG.info("Auto-discovered %d endpoints from system index", len(discovered))
        except Exception as exc:
            LOG.warning("Failed to auto-discover endpoints: %s", exc)

    def _get_tor_router(self):
        if self._tor_router is None:
            try:
                from qb_protocol.communication.tor_vpn_router import tor_vpn_router
                self._tor_router = tor_vpn_router
            except Exception as exc:
                LOG.warning("Tor/VPN router not available: %s", exc)
        return self._tor_router

    def _get_agent(self):
        if self._agent is None:
            try:
                from qb_protocol.agent.agentic_loop import AgenticLoop
                self._agent = AgenticLoop()
            except Exception as exc:
                LOG.warning("Agent loop not available: %s", exc)
        return self._agent

    def _get_gpt_layer(self):
        if self._gpt_layer is None:
            try:
                from qb_protocol.ai.gpt_layer import gpt_layer
                self._gpt_layer = gpt_layer
            except Exception as exc:
                LOG.warning("GPT layer not available: %s", exc)
        return self._gpt_layer

    def _is_self_reference(self, instance_id: str, dimension_id: str) -> bool:
        if instance_id in self._known_instances:
            known = self._known_instances[instance_id]
            if known.get("dimension_id") == dimension_id:
                return True
        return False

    def _can_probe_dimension(self, dimension_id: str) -> Tuple[bool, str]:
        if dimension_id not in self._dimension_exploration:
            return True, "new_dimension"
        
        exploration = self._dimension_exploration[dimension_id]
        last_probe = exploration.get("last_probe_at", "")
        depth = exploration.get("depth", 0)
        probe_count = exploration.get("probe_count", 0)
        
        if depth >= MAX_DISCOVERY_DEPTH:
            return False, f"max_depth_reached:{depth}"
        
        if last_probe:
            try:
                last = datetime.fromisoformat(last_probe.replace("Z", "+00:00")).timestamp()
                if time.time() - last < DISCOVERY_COOLDOWN_SECONDS:
                    return False, "cooldown_active"
            except Exception:
                pass
        
        if probe_count > 100:
            return False, "probe_limit_reached"
        
        return True, "allowed"

    def _record_dimension_probe(self, dimension_id: str, depth: int, probe_path: str):
        if dimension_id not in self._dimension_exploration:
            self._dimension_exploration[dimension_id] = {
                "first_seen": datetime.utcnow().isoformat() + "Z",
                "last_probe_at": datetime.utcnow().isoformat() + "Z",
                "depth": depth,
                "probe_count": 0,
                "probes": [],
            }
        
        exploration = self._dimension_exploration[dimension_id]
        exploration["last_probe_at"] = datetime.utcnow().isoformat() + "Z"
        exploration["probe_count"] = exploration.get("probe_count", 0) + 1
        exploration["depth"] = max(exploration.get("depth", 0), depth)
        exploration.setdefault("probes", []).append({
            "path": probe_path,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        if len(exploration["probes"]) > 1000:
            exploration["probes"] = exploration["probes"][-1000:]
        
        self._save_state()

    def probe_endpoint(self, endpoint: str, path: str, method: str = "GET", params: Dict[str, Any] = None, body: Dict[str, Any] = None, headers: Dict[str, str] = None, timeout: float = 5.0, use_tor: bool = False, use_vpn: bool = False, dimension_id: str = "local") -> Dict[str, Any]:
        """Probe endpoint with self-reference and throttling checks."""
        params = params or {}
        body = body or {}
        headers = headers or {}
        
        instance_id = f"{endpoint}:{path}"
        if self._is_self_reference(instance_id, dimension_id):
            return {
                "endpoint": endpoint,
                "path": path,
                "method": method,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "self_reference",
                "http_code": None,
                "data": None,
                "error": "Known instance - skipping self-reference",
                "latency_ms": 0.0,
                "routed": False,
                "use_tor": use_tor,
                "use_vpn": use_vpn,
            }
        
        can_probe, reason = self._can_probe_dimension(dimension_id)
        if not can_probe:
            return {
                "endpoint": endpoint,
                "path": path,
                "method": method,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "throttled",
                "http_code": None,
                "data": None,
                "error": f"Dimension throttled: {reason}",
                "latency_ms": 0.0,
                "routed": False,
                "use_tor": use_tor,
                "use_vpn": use_vpn,
            }
        
        if endpoint == "local":
            base_url = "http://localhost:17760"
            headers["X-Protocol-Version"] = "2"
        else:
            base_url = endpoint
        
        url = f"{base_url}{path}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query}"
        
        result = {
            "endpoint": endpoint,
            "path": path,
            "method": method,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "error",
            "http_code": None,
            "data": None,
            "error": None,
            "latency_ms": None,
            "routed": False,
            "use_tor": use_tor,
            "use_vpn": use_vpn,
        }
        
        start = time.time()
        try:
            tor_router = self._get_tor_router()
            if tor_router and (use_tor or use_vpn):
                routed_result = tor_router.route_request(url, method, headers, body, timeout, use_tor=use_tor, use_vpn=use_vpn)
                result["status"] = routed_result.get("status", "error")
                result["http_code"] = routed_result.get("http_code")
                result["data"] = routed_result.get("data")
                result["error"] = routed_result.get("error")
                result["latency_ms"] = routed_result.get("latency_ms")
                result["routed"] = routed_result.get("routed", False)
            else:
                import urllib.request
                import urllib.error
                
                req = urllib.request.Request(url, method=method, headers=headers)
                if method == "POST" and body:
                    req.data = json.dumps(body).encode("utf-8")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result["http_code"] = resp.status
                    result["status"] = "ok"
                    result["data"] = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            result["http_code"] = exc.code
            result["error"] = str(exc)
        except Exception as exc:
            result["error"] = str(exc)
        finally:
            if result["latency_ms"] is None:
                result["latency_ms"] = round((time.time() - start) * 1000, 2)
        
        self._known_instances[instance_id] = {
            "dimension_id": dimension_id,
            "last_seen": datetime.utcnow().isoformat() + "Z",
            "status": result["status"],
        }
        self._record_dimension_probe(dimension_id, 0, path)
        return result

    def discover(self, context: str = "general", use_tor: bool = False, use_vpn: bool = False) -> Dict[str, Any]:
        """Multi-step discovery with session management and dimensional limits."""
        if len(self._sessions) >= MAX_ACTIVE_SESSIONS:
            oldest = min(self._sessions.values(), key=lambda s: s.last_probe_at)
            if oldest.session_id in self._sessions:
                self._sessions[oldest.session_id].status = "offloaded"
                self._sessions[oldest.session_id].offloaded = True
                self._sessions[oldest.session_id].offload_location = "alternate_dimension"
        
        session_id = str(uuid.uuid4())
        dimension_id = "local"
        if context.startswith("environment:") or context.startswith("dimension:"):
            parts = context.split(":", 1)
            if len(parts) > 1:
                dimension_id = parts[1].split(":")[0] if ":" in parts[1] else parts[1]
        
        can_probe, reason = self._can_probe_dimension(dimension_id)
        if not can_probe:
            session = DiscoverySession(
                session_id=session_id,
                dimension_id=dimension_id,
                depth=0,
                started_at=datetime.utcnow().isoformat() + "Z",
                last_probe_at=datetime.utcnow().isoformat() + "Z",
                probes_completed=[],
                peers_found=[],
                status="throttled",
                ttl_seconds=DISCOVERY_COOLDOWN_SECONDS,
                metadata={"context": context, "reason": reason},
            )
            with self._lock:
                self._sessions[session_id] = session
            self._save_state()
            return {
                "session_id": session_id,
                "context": context,
                "dimension_id": dimension_id,
                "status": "throttled",
                "reason": reason,
                "use_tor": use_tor,
                "use_vpn": use_vpn,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        
        session = DiscoverySession(
            session_id=session_id,
            dimension_id=dimension_id,
            depth=0,
            started_at=datetime.utcnow().isoformat() + "Z",
            last_probe_at=datetime.utcnow().isoformat() + "Z",
            probes_completed=[],
            peers_found=[],
            status="active",
            ttl_seconds=DISCOVERY_COOLDOWN_SECONDS,
            metadata={"context": context},
        )
        
        with self._lock:
            self._sessions[session_id] = session
        
        raw_probes = []
        for ep in self._endpoints:
            probe = self.probe_endpoint(
                endpoint=ep.endpoint,
                path=ep.path,
                method=ep.method,
                params=ep.params,
                body=ep.body,
                headers=ep.headers,
                timeout=ep.timeout,
                use_tor=use_tor,
                use_vpn=use_vpn,
                dimension_id=dimension_id,
            )
            raw_probes.append(probe)
            session.probes_completed.append(ep.path)
        
        formatted = self.format_with_gpt(raw_probes, context)
        session.status = "completed"
        session.last_probe_at = datetime.utcnow().isoformat() + "Z"
        self._save_state()
        
        try:
            agent = self._get_agent()
            if agent:
                agent_context = {
                    "discovery_session_id": session_id,
                    "discovery_context": context,
                    "dimension_id": dimension_id,
                    "raw_probes": raw_probes,
                    "formatted_results": formatted,
                    "use_tor": use_tor,
                    "use_vpn": use_vpn,
                }
                agent.observe(json.dumps(agent_context, default=str))
        except Exception as exc:
            LOG.warning("Agent observation failed: %s", exc)
        
        return {
            "session_id": session_id,
            "context": context,
            "dimension_id": dimension_id,
            "status": session.status,
            "use_tor": use_tor,
            "use_vpn": use_vpn,
            "raw_probes": raw_probes,
            "formatted": formatted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def format_with_gpt(self, raw_data: List[Dict[str, Any]], context: str = "peer discovery") -> Dict[str, Any]:
        """Use GPT layer to format raw endpoint dumps into structured peer data."""
        gpt = self._get_gpt_layer()
        if not gpt:
            return {"peers": [], "count": 0, "formatted": False}
        
        try:
            compact = json.dumps(raw_data, default=str)[:4000]
            prompt = (
                f"Format this raw API data into structured peer discovery results. "
                f"Context: {context}. "
                f"Return JSON with keys: peers (list), count (int), summary (string). "
                f"Each peer should have: user_id, device_id, btc_public_address, environment_type, environment_id, geo, signal_strength. "
                f"Raw data: {compact}"
            )
            result = gpt.query(prompt, max_tokens=1024, temperature=0.3)
            raw = result.get("response", "") if isinstance(result, dict) else str(result)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(raw[start:end + 1])
                if isinstance(parsed, dict):
                    parsed["formatted"] = True
                    return parsed
        except Exception as exc:
            LOG.warning("GPT formatting failed: %s", exc)
        return {"peers": [], "count": 0, "formatted": False, "error": "gpt_format_failed"}

    def get_registry_dump(self, use_tor: bool = False) -> Dict[str, Any]:
        """Registry dump with throttling."""
        raw_dump = []
        
        try:
            from qb_protocol.communication.celestial_router import celestial_router
            dims = celestial_router.get_dimensions()
            raw_dump.append({
                "endpoint": "local",
                "path": "/communication/dimensions",
                "method": "GET",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "ok",
                "http_code": 200,
                "data": dims,
                "error": None,
                "latency_ms": 0.0,
                "routed": False,
                "use_tor": use_tor,
                "use_vpn": False,
            })
        except Exception as exc:
            raw_dump.append({"endpoint": "local", "path": "/communication/dimensions", "method": "GET", "timestamp": datetime.utcnow().isoformat() + "Z", "status": "error", "http_code": None, "data": None, "error": str(exc), "latency_ms": 0.0, "routed": False, "use_tor": use_tor, "use_vpn": False})
        
        try:
            portals = self.get_live_portals()
            raw_dump.append({
                "endpoint": "local",
                "path": "/communication/portals/live",
                "method": "GET",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "ok",
                "http_code": 200,
                "data": portals,
                "error": None,
                "latency_ms": 0.0,
                "routed": False,
                "use_tor": use_tor,
                "use_vpn": False,
            })
        except Exception as exc:
            raw_dump.append({"endpoint": "local", "path": "/communication/portals/live", "method": "GET", "timestamp": datetime.utcnow().isoformat() + "Z", "status": "error", "http_code": None, "data": None, "error": str(exc), "latency_ms": 0.0, "routed": False, "use_tor": use_tor, "use_vpn": False})
        
        try:
            from qb_protocol.mesh_rewards.multiverse_ranker import multiverse_ranker
            leaderboard = multiverse_ranker.get_leaderboard("global", 100)
            raw_dump.append({
                "endpoint": "local",
                "path": "/mesh-rewards/multiverse/leaderboard",
                "method": "GET",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "ok",
                "http_code": 200,
                "data": {"leaderboard": leaderboard},
                "error": None,
                "latency_ms": 0.0,
                "routed": False,
                "use_tor": use_tor,
                "use_vpn": False,
            })
        except Exception as exc:
            raw_dump.append({"endpoint": "local", "path": "/mesh-rewards/multiverse/leaderboard", "method": "GET", "timestamp": datetime.utcnow().isoformat() + "Z", "status": "error", "http_code": None, "data": None, "error": str(exc), "latency_ms": 0.0, "routed": False, "use_tor": use_tor, "use_vpn": False})
        
        try:
            from qb_protocol.mesh_rewards.celestial_nodes import celestial_node_manager
            assignments = {}
            for node_id, node in celestial_node_manager.nodes.items():
                env_key = f"{node.environment_type}/{node.environment_id}"
                if env_key not in assignments:
                    assignments[env_key] = []
                assignments[env_key].append({"node_id": node_id, "user_id": node.user_id, "device_id": node.device_id, "btc_public_address": node.btc_public_address})
            raw_dump.append({
                "endpoint": "local",
                "path": "/mesh-rewards/celestial/router/assignments",
                "method": "GET",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "ok",
                "http_code": 200,
                "data": {"assignments": assignments, "source": "celestial_router"},
                "error": None,
                "latency_ms": 0.0,
                "routed": False,
                "use_tor": use_tor,
                "use_vpn": False,
            })
        except Exception as exc:
            raw_dump.append({"endpoint": "local", "path": "/mesh-rewards/celestial/router/assignments", "method": "GET", "timestamp": datetime.utcnow().isoformat() + "Z", "status": "error", "http_code": None, "data": None, "error": str(exc), "latency_ms": 0.0, "routed": False, "use_tor": use_tor, "use_vpn": False})
        
        formatted = self.format_with_gpt(raw_dump, "registry dump")
        return {
            "use_tor": use_tor,
            "raw_dump": raw_dump,
            "formatted": formatted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def get_live_portals(self, requester_device_id: str = "") -> List[Dict[str, Any]]:
        portals = []
        try:
            from qb_protocol.communication.celestial_router import celestial_router
            dimensions = celestial_router.get_dimensions()
            for dim in dimensions:
                dim_id = dim.get("dimension_id", "")
                portals.append({
                    "dimension_id": dim_id,
                    "name": dim.get("name", ""),
                    "universe": dim.get("universe", ""),
                    "coordinates": dim.get("coordinates", {}),
                    "stability": dim.get("stability", 0.0),
                    "peer_count": 0,
                    "live_peers": [],
                    "portal_url": dim.get("metadata", {}).get("portal_url"),
                })
        except Exception as exc:
            LOG.warning("Live portal discovery failed: %s", exc)
        portals.sort(key=lambda p: p.get("stability", 0.0), reverse=True)
        return portals

    def add_endpoint(self, endpoint: str, method: str, path: str, timeout: float = 5.0, headers: Dict[str, str] = None, params: Dict[str, Any] = None, body: Dict[str, Any] = None):
        ep = EndpointProbe(
            endpoint=endpoint,
            method=method,
            path=path,
            timeout=timeout,
            retries=2,
            headers=headers or {},
            params=params or {},
            body=body or {},
        )
        with self._lock:
            self._endpoints.append(ep)

    def setup_browser_automation_for_discovered(self, min_machines: int = 2) -> Dict[str, Any]:
        portals = self.get_live_portals()
        result = {
            "portals_found": len(portals),
            "min_required": min_machines,
            "browser_setup_triggered": False,
            "missions_created": 0,
            "trackers_registered": 0,
        }

        if len(portals) < min_machines:
            return result

        try:
            from qb_protocol.communication.browser_session import browser_session_manager
            for portal in portals:
                portal_url = portal.get("portal_url")
                if portal_url:
                    browser_session_manager.register_tracker(
                        endpoint=portal_url,
                        metadata={
                            "dimension_id": portal.get("dimension_id"),
                            "stability": portal.get("stability", 0.0),
                            "source": "peer_discovery",
                        },
                    )
                    result["trackers_registered"] += 1

            try:
                from qb_protocol.orchestrator.incognito_missions import incognito_mission_runner
                for portal in portals:
                    portal_url = portal.get("portal_url")
                    if portal_url:
                        mission = incognito_mission_runner.create_mission(
                            mission_type="browser_automation",
                            payload={
                                "action": "discover",
                                "endpoints": [portal_url],
                                "profile_name": f"auto-{portal.get('dimension_id', 'unknown')}",
                            },
                            incognito=True,
                            priority=3,
                        )
                        result["missions_created"] += 1
            except Exception as exc:
                LOG.warning("Failed to create browser automation missions: %s", exc)

            result["browser_setup_triggered"] = True
        except Exception as exc:
            LOG.warning("Browser automation setup failed: %s", exc)
            result["error"] = str(exc)

        return result

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_endpoints": len(self._endpoints),
            "active_sessions": len(self._sessions),
            "dimensions_tracked": len(self._dimension_exploration),
            "known_instances": len(self._known_instances),
            "agent_available": self._get_agent() is not None,
            "gpt_available": self._get_gpt_layer() is not None,
            "tor_socks": f"{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
            "vpn_interface": VPN_INTERFACE,
            "max_depth": MAX_DISCOVERY_DEPTH,
            "cooldown_seconds": DISCOVERY_COOLDOWN_SECONDS,
            "max_active_sessions": MAX_ACTIVE_SESSIONS,
        }


live_discovery = LiveDiscovery()

#!/usr/bin/env python3
"""
QB Protocol - Peer Discovery
Live-measured discovery system. No local peer storage.
Devices are discovered by querying live endpoints, formatting via GPT,
and routing through Tor/VPN when needed.
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


class LiveDiscovery:
    """Discovers peers by measuring live endpoints, not local storage."""

    def __init__(self):
        self._lock = threading.Lock()
        self._endpoints: List[EndpointProbe] = []
        self._agent = None
        self._gpt_layer = None
        self._tor_router = None
        self._register_default_endpoints()

    def _get_tor_router(self):
        if self._tor_router is None:
            try:
                from qb_protocol.communication.tor_vpn_router import tor_vpn_router
                self._tor_router = tor_vpn_router
            except Exception as exc:
                LOG.warning("Tor/VPN router not available: %s", exc)
        return self._tor_router

    def _register_default_endpoints(self):
        self._endpoints = [
            EndpointProbe(endpoint="local", method="GET", path="/communication/peers/discover", timeout=5.0, retries=2, headers={}, params={}, body={}),
            EndpointProbe(endpoint="local", method="POST", path="/communication/peers/discover/geo", timeout=5.0, retries=2, headers={"Content-Type": "application/json"}, params={}, body={}),
            EndpointProbe(endpoint="local", method="POST", path="/communication/peers/discover/btc-rank", timeout=5.0, retries=2, headers={"Content-Type": "application/json"}, params={}, body={}),
            EndpointProbe(endpoint="local", method="GET", path="/communication/portals/live", timeout=5.0, retries=2, headers={}, params={}, body={}),
            EndpointProbe(endpoint="local", method="GET", path="/communication/dimensions", timeout=5.0, retries=2, headers={}, body={}),
            EndpointProbe(endpoint="local", method="GET", path="/mesh-rewards/multiverse/leaderboard", timeout=5.0, retries=2, headers={}, params={}, body={}),
            EndpointProbe(endpoint="local", method="POST", path="/mesh-rewards/celestial/nodes/register", timeout=5.0, retries=2, headers={"Content-Type": "application/json"}, params={}, body={}),
            EndpointProbe(endpoint="local", method="GET", path="/mesh-rewards/celestial/router/assignments", timeout=5.0, retries=2, headers={}, params={}, body={}),
        ]

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

    def probe_endpoint(self, endpoint: str, path: str, method: str = "GET", params: Dict[str, Any] = None, body: Dict[str, Any] = None, headers: Dict[str, str] = None, timeout: float = 5.0, use_tor: bool = False, use_vpn: bool = False) -> Dict[str, Any]:
        """Probe a live endpoint and return raw measured data."""
        params = params or {}
        body = body or {}
        headers = headers or {}
        
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
        
        return result

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

    def discover(self, context: str = "general", use_tor: bool = False, use_vpn: bool = False) -> Dict[str, Any]:
        """Discover peers by probing live endpoints and formatting results."""
        import re
        
        device_id = ""
        try:
            from qb_protocol.matter_energy import matter_energy
            if HAS_MATTER_ENERGY:
                identity = matter_energy.get_latest_snapshot("self")
                if identity:
                    device_id = identity.get("device_id", "")
        except Exception:
            pass
        
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
            )
            raw_probes.append(probe)
        
        formatted = self.format_with_gpt(raw_probes, context)
        
        try:
            agent = self._get_agent()
            if agent:
                agent_context = {
                    "discovery_context": context,
                    "raw_probes": raw_probes,
                    "formatted_results": formatted,
                    "use_tor": use_tor,
                    "use_vpn": use_vpn,
                }
                agent.observe(json.dumps(agent_context, default=str))
        except Exception as exc:
            LOG.warning("Agent observation failed: %s", exc)
        
        return {
            "context": context,
            "use_tor": use_tor,
            "use_vpn": use_vpn,
            "raw_probes": raw_probes,
            "formatted": formatted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def discover_geo(self, lat: float, lon: float, radius_km: float = GEO_TOLERANCE_KM, use_tor: bool = False) -> Dict[str, Any]:
        geo_body = {"lat": lat, "lon": lon, "radius_km": radius_km, "device_id": ""}
        geo_probe = self.probe_endpoint("local", "/communication/peers/discover/geo", "POST", body=geo_body, headers={"Content-Type": "application/json"})
        
        formatted = self.format_with_gpt([geo_probe], "geo discovery")
        return {
            "lat": lat,
            "lon": lon,
            "radius_km": radius_km,
            "use_tor": use_tor,
            "raw": geo_probe,
            "formatted": formatted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def discover_btc_rank(self, environment_type: str = "global", limit: int = 50, use_tor: bool = False) -> Dict[str, Any]:
        btc_body = {"environment_type": environment_type, "limit": limit, "device_id": ""}
        btc_probe = self.probe_endpoint("local", "/communication/peers/discover/btc-rank", "POST", body=btc_body, headers={"Content-Type": "application/json"})
        
        formatted = self.format_with_gpt([btc_probe], "btc rank discovery")
        return {
            "environment_type": environment_type,
            "limit": limit,
            "use_tor": use_tor,
            "raw": btc_probe,
            "formatted": formatted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def get_registry_dump(self, use_tor: bool = False) -> Dict[str, Any]:
        """Dump live registry state from actual endpoints - no local storage."""
        endpoints = [
            ("GET", "/communication/peers/discover", {}),
            ("GET", "/communication/portals/live", {}),
            ("GET", "/communication/dimensions", {}),
            ("GET", "/communication/coordinates", {}),
            ("GET", "/mesh-rewards/multiverse/leaderboard?environment_type=global&limit=100", {}),
            ("GET", "/mesh-rewards/celestial/router/assignments", {}),
            ("GET", "/mesh-rewards/rewards/leaderboard?window_seconds=86400", {}),
        ]
        
        raw_dump = []
        for method, path, params in endpoints:
            probe = self.probe_endpoint("local", path, method, params=params)
            raw_dump.append(probe)
        
        formatted = self.format_with_gpt(raw_dump, "registry dump")
        return {
            "use_tor": use_tor,
            "raw_dump": raw_dump,
            "formatted": formatted,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

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

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_endpoints": len(self._endpoints),
            "agent_available": self._get_agent() is not None,
            "gpt_available": self._get_gpt_layer() is not None,
            "tor_socks": f"{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
            "vpn_interface": VPN_INTERFACE,
        }


live_discovery = LiveDiscovery()

#!/usr/bin/env python3
"""
QB Protocol - Communication: Tor/VPN Routing
Routes discovery requests through Tor SOCKS or VPN interfaces.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
from typing import Dict, Any, Optional
from pathlib import Path

LOG = logging.getLogger("qb_protocol.communication.routing")

TOR_SOCKS_HOST = os.environ.get("TOR_SOCKS_HOST", "127.0.0.1")
TOR_SOCKS_PORT = int(os.environ.get("TOR_SOCKS_PORT", "9050"))
VPN_INTERFACE = os.environ.get("VPN_INTERFACE", "utun")


class TorVPNRouter:
    """Routes HTTP requests through Tor SOCKS proxy or VPN interface."""

    def __init__(self):
        self.tor_available = False
        self.vpn_active = False
        self._check_availability()

    def _check_availability(self):
        self.tor_available = self._check_tor_socks()
        self.vpn_active = self._check_vpn_interface()
        LOG.info("Tor available: %s, VPN active: %s", self.tor_available, self.vpn_active)

    def _check_tor_socks(self) -> bool:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((TOR_SOCKS_HOST, TOR_SOCKS_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _check_vpn_interface(self) -> bool:
        try:
            return os.path.exists(f"/dev/{VPN_INTERFACE}") or any(VPN_INTERFACE in iface for iface in os.listdir("/dev") if os.path.isdir(f"/dev/{iface}"))
        except Exception:
            return False

    def route_request(self, url: str, method: str = "GET", headers: Dict[str, str] = None, body: Dict[str, Any] = None, timeout: float = 10.0, use_tor: bool = False, use_vpn: bool = False) -> Dict[str, Any]:
        """Route HTTP request through Tor or VPN if requested and available."""
        headers = headers or {}
        body = body or {}
        
        result = {
            "url": url,
            "method": method,
            "use_tor": use_tor and self.tor_available,
            "use_vpn": use_vpn and self.vpn_active,
            "routed": False,
            "http_code": None,
            "data": None,
            "error": None,
            "latency_ms": None,
        }
        
        start = time.time()
        try:
            if use_tor and self.tor_available:
                result["routed"] = True
                result["data"] = self._request_via_tor(url, method, headers, body, timeout)
            elif use_vpn and self.vpn_active:
                result["routed"] = True
                result["data"] = self._request_via_vpn(url, method, headers, body, timeout)
            else:
                import urllib.request
                req = urllib.request.Request(url, method=method, headers=headers)
                if method == "POST" and body:
                    req.data = json.dumps(body).encode("utf-8")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result["http_code"] = resp.status
                    result["data"] = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            result["error"] = str(exc)
        finally:
            result["latency_ms"] = round((time.time() - start) * 1000, 2)
        return result

    def _request_via_tor(self, url: str, method: str, headers: Dict[str, str], body: Dict[str, Any], timeout: float) -> Any:
        try:
            import socks
            import socket
            import urllib.request
            import urllib.error
            
            original_socket = socket.socket
            socket.socket = socks.socksocket
            socks.set_default_proxy(socks.SOCKS5, TOR_SOCKS_HOST, TOR_SOCKS_PORT)
            socket.socket = socks.socksocket
            
            req = urllib.request.Request(url, method=method, headers=headers)
            if method == "POST" and body:
                req.data = json.dumps(body).encode("utf-8")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                socket.socket = original_socket
                return json.loads(resp.read().decode("utf-8"))
        except ImportError:
            raise RuntimeError("PySocks not installed. Install with: pip install pysocks")
        except Exception:
            try:
                socket.socket = original_socket
            except Exception:
                pass
            raise

    def _request_via_vpn(self, url: str, method: str, headers: Dict[str, str], body: Dict[str, Any], timeout: float) -> Any:
        import urllib.request
        req = urllib.request.Request(url, method=method, headers=headers)
        if method == "POST" and body:
            req.data = json.dumps(body).encode("utf-8")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get_status(self) -> Dict[str, Any]:
        return {
            "tor_available": self.tor_available,
            "tor_socks": f"{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
            "vpn_active": self.vpn_active,
            "vpn_interface": VPN_INTERFACE,
        }


tor_vpn_router = TorVPNRouter()

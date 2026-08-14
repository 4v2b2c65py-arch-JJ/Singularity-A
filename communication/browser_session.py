#!/usr/bin/env python3
"""
QB Protocol - Browser Session Manager
Persistent cookie profiles, rate-limited browser automation,
and alive/inactive tracker registry integration.
"""

import os
import sys
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

LOG = logging.getLogger("qb_protocol.browser_session")

COOKIE_PROFILES_PATH = Path.home() / ".qb_protocol_browser_profiles.json"
BROWSER_STATE_PATH = Path.home() / ".qb_protocol_browser_state.json"


@dataclass
class CookieProfile:
    profile_id: str
    name: str
    cookies: Dict[str, Any]
    created_at: str
    last_used_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserTracker:
    tracker_id: str
    endpoint: str
    status: str
    last_seen: str
    response_time_ms: float
    cookie_profile_id: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BrowserSessionManager:
    """Manages persistent browser cookie profiles with rate limiting."""

    def __init__(self):
        self._lock = threading.Lock()
        self._profiles: Dict[str, CookieProfile] = {}
        self._trackers: Dict[str, BrowserTracker] = {}
        self._rate_limiter = None
        self._load_profiles()
        self._load_state()

    def _get_rate_limiter(self):
        if self._rate_limiter is None:
            try:
                from qb_protocol.package.node_service_package import rate_limiter
                self._rate_limiter = rate_limiter
            except Exception as exc:
                LOG.warning("Rate limiter not available: %s", exc)
        return self._rate_limiter

    def _load_profiles(self):
        if COOKIE_PROFILES_PATH.exists():
            try:
                with open(COOKIE_PROFILES_PATH, "r") as f:
                    data = json.load(f)
                for pid, p in data.get("profiles", {}).items():
                    self._profiles[pid] = CookieProfile(**p)
                LOG.info("Loaded %d cookie profiles", len(self._profiles))
            except Exception as exc:
                LOG.warning("Failed to load cookie profiles: %s", exc)

    def _save_profiles(self):
        try:
            with open(COOKIE_PROFILES_PATH, "w") as f:
                json.dump({
                    "profiles": {pid: asdict(p) for pid, p in self._profiles.items()},
                }, f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save cookie profiles: %s", exc)

    def _load_state(self):
        if BROWSER_STATE_PATH.exists():
            try:
                with open(BROWSER_STATE_PATH, "r") as f:
                    data = json.load(f)
                for tid, t in data.get("trackers", {}).items():
                    self._trackers[tid] = BrowserTracker(**t)
                LOG.info("Loaded %d browser trackers", len(self._trackers))
            except Exception as exc:
                LOG.warning("Failed to load browser state: %s", exc)

    def _save_state(self):
        try:
            with open(BROWSER_STATE_PATH, "w") as f:
                json.dump({
                    "trackers": {tid: asdict(t) for tid, t in self._trackers.items()},
                }, f, indent=2, default=str)
        except Exception as exc:
            LOG.warning("Failed to save browser state: %s", exc)

    def create_profile(self, name: str, initial_cookies: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> CookieProfile:
        profile = CookieProfile(
            profile_id=str(uuid.uuid4()),
            name=name,
            cookies=initial_cookies or {},
            created_at=datetime.utcnow().isoformat() + "Z",
            last_used_at=datetime.utcnow().isoformat() + "Z",
            metadata=metadata or {},
        )
        with self._lock:
            self._profiles[profile.profile_id] = profile
        self._save_profiles()
        LOG.info("Created cookie profile: %s", profile.profile_id)
        return profile

    def get_profile(self, profile_id: str) -> Optional[CookieProfile]:
        return self._profiles.get(profile_id)

    def update_profile_cookies(self, profile_id: str, cookies: Dict[str, Any]):
        profile = self._profiles.get(profile_id)
        if not profile:
            return None
        profile.cookies.update(cookies)
        profile.last_used_at = datetime.utcnow().isoformat() + "Z"
        self._save_profiles()
        return profile

    def register_tracker(self, endpoint: str, cookie_profile_id: Optional[str] = None, metadata: Dict[str, Any] = None) -> BrowserTracker:
        tracker = BrowserTracker(
            tracker_id=str(uuid.uuid4()),
            endpoint=endpoint,
            status="active",
            last_seen=datetime.utcnow().isoformat() + "Z",
            response_time_ms=0.0,
            cookie_profile_id=cookie_profile_id,
            metadata=metadata or {},
        )
        with self._lock:
            self._trackers[tracker.tracker_id] = tracker
        self._save_state()
        LOG.info("Registered browser tracker: %s -> %s", tracker.tracker_id, endpoint)
        return tracker

    def update_tracker_status(self, tracker_id: str, status: str, response_time_ms: float = 0.0):
        tracker = self._trackers.get(tracker_id)
        if not tracker:
            return None
        tracker.status = status
        tracker.last_seen = datetime.utcnow().isoformat() + "Z"
        tracker.response_time_ms = response_time_ms
        self._save_state()
        return tracker

    def get_alive_trackers(self) -> List[Dict[str, Any]]:
        now = time.time()
        alive = []
        for t in self._trackers.values():
            if t.status == "active":
                try:
                    last = datetime.fromisoformat(t.last_seen.replace("Z", "+00:00")).timestamp()
                    if now - last < 300:
                        alive.append(asdict(t))
                except Exception:
                    pass
        return alive

    def get_inactive_trackers(self) -> List[Dict[str, Any]]:
        now = time.time()
        inactive = []
        for t in self._trackers.values():
            if t.status != "active":
                try:
                    last = datetime.fromisoformat(t.last_seen.replace("Z", "+00:00")).timestamp()
                    if now - last < 86400:
                        inactive.append(asdict(t))
                except Exception:
                    pass
        return inactive

    def get_registry(self) -> Dict[str, Any]:
        return {
            "total_profiles": len(self._profiles),
            "total_trackers": len(self._trackers),
            "alive_trackers": len(self.get_alive_trackers()),
            "inactive_trackers": len(self.get_inactive_trackers()),
            "trackers": [asdict(t) for t in self._trackers.values()],
        }

    def request_with_profile(self, profile_id: str, url: str, method: str = "GET", headers: Dict[str, str] = None, data: Dict[str, Any] = None, timeout: float = 10.0) -> Dict[str, Any]:
        rate_limiter = self._get_rate_limiter()
        if rate_limiter and not rate_limiter.allow("browser_session"):
            return {
                "status": "error",
                "error": "rate_limited",
                "http_code": None,
                "latency_ms": 0.0,
            }

        profile = self._profiles.get(profile_id)
        if not profile:
            return {
                "status": "error",
                "error": "profile_not_found",
                "http_code": None,
                "latency_ms": 0.0,
            }

        import requests

        session = requests.Session()
        for name, value in profile.cookies.items():
            session.cookies.set(name, value)

        req_headers = {"User-Agent": "QB-Protocol-Browser/2.0"}
        if headers:
            req_headers.update(headers)

        start = time.time()
        try:
            if method.upper() == "GET":
                resp = session.get(url, headers=req_headers, timeout=timeout)
            else:
                resp = session.post(url, headers=req_headers, json=data, timeout=timeout)

            latency_ms = round((time.time() - start) * 1000, 2)
            self.update_profile_cookies(profile_id, dict(session.cookies))
            return {
                "status": "ok" if resp.status_code < 400 else "error",
                "http_code": resp.status_code,
                "data": resp.text[:4000],
                "latency_ms": latency_ms,
            }
        except Exception as exc:
            latency_ms = round((time.time() - start) * 1000, 2)
            return {
                "status": "error",
                "error": str(exc),
                "http_code": None,
                "latency_ms": latency_ms,
            }

    def discover_browser_targets(self, endpoints: List[str]) -> List[Dict[str, Any]]:
        results = []
        for endpoint in endpoints:
            tracker_id = None
            for tid, t in self._trackers.items():
                if t.endpoint == endpoint:
                    tracker_id = tid
                    break

            if not tracker_id:
                tracker = self.register_tracker(endpoint)
                tracker_id = tracker.tracker_id

            start = time.time()
            try:
                import requests
                resp = requests.get(endpoint, timeout=5)
                latency_ms = round((time.time() - start) * 1000, 2)
                status = "active" if resp.status_code < 400 else "inactive"
                self.update_tracker_status(tracker_id, status, latency_ms)
                results.append({
                    "tracker_id": tracker_id,
                    "endpoint": endpoint,
                    "status": status,
                    "http_code": resp.status_code,
                    "latency_ms": latency_ms,
                })
            except Exception as exc:
                latency_ms = round((time.time() - start) * 1000, 2)
                self.update_tracker_status(tracker_id, "inactive", latency_ms)
                results.append({
                    "tracker_id": tracker_id,
                    "endpoint": endpoint,
                    "status": "inactive",
                    "http_code": None,
                    "error": str(exc),
                    "latency_ms": latency_ms,
                })
        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_profiles": len(self._profiles),
            "total_trackers": len(self._trackers),
            "alive_trackers": len(self.get_alive_trackers()),
            "inactive_trackers": len(self.get_inactive_trackers()),
            "profiles_path": str(COOKIE_PROFILES_PATH),
            "state_path": str(BROWSER_STATE_PATH),
        }


browser_session_manager = BrowserSessionManager()

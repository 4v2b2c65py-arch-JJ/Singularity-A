#!/usr/bin/env python3
"""
QB Protocol - Peer Discovery
Discovers other individuals connected via the same service across
environments, timelines, planes, realms, and dimensions using
celestial router, satellite geo-data, and BTC wallet addresses.
"""

import os
import sys
import time
import uuid
import json
import math
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

LOG = logging.getLogger("qb_protocol.peer_discovery")

GEO_TOLERANCE_KM = 50.0
SIGNAL_MATCH_THRESHOLD = 0.7


@dataclass
class PeerRecord:
    peer_id: str
    user_id: str
    device_id: str
    environment_type: str
    environment_id: str
    dimension_id: str
    btc_public_address: str
    geo: Dict[str, Any]
    signal_strength: float
    last_seen: str
    portal_url: Optional[str]
    metadata: Dict[str, Any]


class PeerDiscovery:
    """Discovers peers across the multiverse using celestial router and satellite geo-data."""

    def __init__(self):
        self.peers: Dict[str, PeerRecord] = {}
        self._lock = threading.Lock()
        self._satellite_handler = None

    def register_peer(self, peer: PeerRecord):
        with self._lock:
            self.peers[peer.peer_id] = peer
        LOG.info("Peer discovered: %s in %s/%s", peer.peer_id, peer.environment_type, peer.environment_id)

    def discover_in_environment(self, environment_type: str, environment_id: str, requester_device_id: str) -> List[Dict[str, Any]]:
        results = []
        with self._lock:
            for peer in self.peers.values():
                if peer.environment_type == environment_type and peer.environment_id == environment_id:
                    if peer.device_id != requester_device_id:
                        results.append(asdict(peer))
        return results

    def discover_linked_environments(self, dimension_id: str, requester_device_id: str) -> List[Dict[str, Any]]:
        results = []
        try:
            from qb_protocol.communication.celestial_router import celestial_router
            dim = celestial_router.get_dimension(dimension_id)
            if not dim:
                return results
            linked = dim.get("connections", [])
            with self._lock:
                for peer in self.peers.values():
                    if peer.dimension_id == dimension_id or peer.dimension_id in linked:
                        if peer.device_id != requester_device_id:
                            results.append(asdict(peer))
        except Exception as exc:
            LOG.warning("Linked environment discovery failed: %s", exc)
        return results

    def discover_by_geo(self, lat: float, lon: float, radius_km: float = GEO_TOLERANCE_KM, requester_device_id: str = "") -> List[Dict[str, Any]]:
        results = []
        with self._lock:
            for peer in self.peers.values():
                if peer.device_id == requester_device_id:
                    continue
                peer_lat = peer.geo.get("lat", 0.0)
                peer_lon = peer.geo.get("lon", 0.0)
                distance = self._haversine_km(lat, lon, peer_lat, peer_lon)
                if distance <= radius_km:
                    record = asdict(peer)
                    record["distance_km"] = round(distance, 2)
                    results.append(record)
        results.sort(key=lambda r: r.get("distance_km", float("inf")))
        return results

    def discover_by_wallet(self, btc_public_address: str, requester_device_id: str = "") -> List[Dict[str, Any]]:
        results = []
        with self._lock:
            for peer in self.peers.values():
                if peer.device_id == requester_device_id:
                    continue
                if peer.btc_public_address == btc_public_address:
                    results.append(asdict(peer))
        return results

    def discover_by_btc_rank(self, environment_type: str = "global", limit: int = 50, requester_device_id: str = "") -> List[Dict[str, Any]]:
        results = []
        try:
            from qb_protocol.mesh_rewards.multiverse_ranker import multiverse_ranker
            leaderboard = multiverse_ranker.get_leaderboard(environment_type, limit)
            with self._lock:
                for entry in leaderboard:
                    address = entry.get("address", "")
                    user_id = entry.get("user_id", "")
                    for peer in self.peers.values():
                        if peer.device_id == requester_device_id:
                            continue
                        if peer.btc_public_address == address or peer.user_id == user_id:
                            record = asdict(peer)
                            record["sats"] = entry.get("sats", 0)
                            record["rank"] = entry.get("rank", 0)
                            record["btc_value_usd"] = entry.get("btc_value_usd", 0.0)
                            results.append(record)
        except Exception as exc:
            LOG.warning("BTC rank discovery failed: %s", exc)
        return results

    def get_live_portals(self, requester_device_id: str = "") -> List[Dict[str, Any]]:
        portals = []
        try:
            from qb_protocol.communication.celestial_router import celestial_router
            dimensions = celestial_router.get_dimensions()
            with self._lock:
                for dim in dimensions:
                    dim_id = dim.get("dimension_id", "")
                    peers_in_dim = [asdict(p) for p in self.peers.values() if p.dimension_id == dim_id and p.device_id != requester_device_id]
                    if peers_in_dim or dim.get("stability", 0) > 0.5:
                        portals.append({
                            "dimension_id": dim_id,
                            "name": dim.get("name", ""),
                            "universe": dim.get("universe", ""),
                            "coordinates": dim.get("coordinates", {}),
                            "stability": dim.get("stability", 0.0),
                            "peer_count": len(peers_in_dim),
                            "live_peers": peers_in_dim,
                            "portal_url": dim.get("metadata", {}).get("portal_url"),
                        })
        except Exception as exc:
            LOG.warning("Live portal discovery failed: %s", exc)
        portals.sort(key=lambda p: p.get("stability", 0.0), reverse=True)
        return portals

    def match_peers_by_signal(self, device_id: str, signal_strength: float) -> List[Dict[str, Any]]:
        results = []
        with self._lock:
            for peer in self.peers.values():
                if peer.device_id == device_id:
                    continue
                match_score = self._calculate_signal_match(signal_strength, peer.signal_strength)
                if match_score >= SIGNAL_MATCH_THRESHOLD:
                    record = asdict(peer)
                    record["signal_match_score"] = round(match_score, 2)
                    results.append(record)
        results.sort(key=lambda r: r.get("signal_match_score", 0.0), reverse=True)
        return results

    def _calculate_signal_match(self, signal_a: float, signal_b: float) -> float:
        if signal_a <= 0 or signal_b <= 0:
            return 0.0
        ratio = min(signal_a, signal_b) / max(signal_a, signal_b)
        return ratio

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        phi1 = self._rad(lat1)
        phi2 = self._rad(lat2)
        dphi = self._rad(lat2 - lat1)
        dlambda = self._rad(lon2 - lon1)
        a = (1 - math.cos(dphi) + math.cos(phi1) * math.cos(phi2) * (1 - math.cos(dlambda))) / 2
        return 2 * R * math.asin(math.sqrt(a))

    def _rad(self, deg: float) -> float:
        return deg * math.pi / 180.0

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_peers": len(self.peers),
                "environments": list(set(p.environment_type for p in self.peers.values())),
            }


peer_discovery = PeerDiscovery()

#!/usr/bin/env python3
"""
QB Protocol - Satellite UDP Bridge
Local authenticated bridge between modem and API server.
Binds only to 127.0.0.1. No public exposure.
"""

import json
import time
import socket
import threading
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

LOG = logging.getLogger("qb_protocol.satellite.udp_bridge")


class UDPBridge:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9100,
        secret: str = "",
        max_packet_size: int = 2048,
        max_age_seconds: int = 120,
    ):
        self.host = host
        self.port = port
        self.secret = secret or "qb-protocol-satellite-bridge"
        self.max_packet_size = max_packet_size
        self.max_age_seconds = max_age_seconds
        self.sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sequence_store: Dict[str, int] = {}
        self._lock = threading.RLock()

    def start(self, handler: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(True)
        self._running = True
        self._handler = handler
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        LOG.info(f"UDP bridge listening on {self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2)
        LOG.info("UDP bridge stopped")

    def _listen(self) -> None:
        while self._running:
            try:
                raw, address = self.sock.recvfrom(self.max_packet_size)
                packet = self._validate(raw, address)
                if packet and self._handler:
                    try:
                        self._handler(packet)
                    except Exception as e:
                        LOG.error(f"UDP handler error: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    LOG.error(f"UDP listen error: {e}")

    def _validate(self, raw: bytes, address) -> Optional[Dict[str, Any]]:
        try:
            packet = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            LOG.warning(f"Dropped malformed packet from {address}")
            return None

        if packet.get("version") != 2:
            LOG.warning(f"Dropped protocol mismatch from {address}: {packet.get('version')}")
            return None

        timestamp = packet.get("timestamp")
        if not isinstance(timestamp, int):
            LOG.warning(f"Dropped packet with invalid timestamp from {address}")
            return None

        if abs(int(time.time()) - timestamp) > self.max_age_seconds:
            LOG.warning(f"Dropped stale packet from {address}")
            return None

        sequence = packet.get("sequence")
        if not isinstance(sequence, int):
            LOG.warning(f"Dropped packet with invalid sequence from {address}")
            return None

        device_id = packet.get("device_id", "")
        if not device_id:
            LOG.warning(f"Dropped packet with missing device_id from {address}")
            return None

        with self._lock:
            last_seq = self._sequence_store.get(device_id, -1)
            if sequence <= last_seq:
                LOG.warning(f"Dropped replay packet from {device_id}: seq={sequence}")
                return None
            self._sequence_store[device_id] = sequence

        mac = packet.get("mac", "")
        if not mac:
            LOG.warning(f"Dropped packet with missing MAC from {address}")
            return None

        payload = packet.get("payload", "")
        expected_mac = self._compute_mac(device_id, sequence, timestamp, payload)
        if not hmac.compare_digest(mac, expected_mac):
            LOG.warning(f"Dropped packet with invalid MAC from {address}")
            return None

        return packet

    def _compute_mac(self, device_id: str, sequence: int, timestamp: int, payload: str) -> str:
        data = f"{device_id}:{sequence}:{timestamp}:{payload}"
        return hmac.new(self.secret.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]

    def send(self, packet: Dict[str, Any], target: tuple) -> None:
        if not self.sock:
            return
        raw = json.dumps(packet).encode("utf-8")
        self.sock.sendto(raw, target)


udp_bridge = UDPBridge()

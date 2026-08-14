#!/usr/bin/env python3
"""
QB Protocol - Keepalive TCP Client Manager
Persistent TCP client connections with keepalive, reconnect, and heartbeat.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import threading
import socket
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.orchestrator.keepalive")


@dataclass
class TCPClientConfig:
    host: str
    port: int
    timeout: float = 5.0
    keepalive_idle: int = 60
    keepalive_interval: int = 10
    keepalive_count: int = 3
    reconnect: bool = True
    reconnect_backoff: float = 2.0
    max_reconnect_attempts: int = 10
    use_tls: bool = False


@dataclass
class TCPClientState:
    client_id: str
    config: Dict[str, Any]
    connected: bool
    last_heartbeat: str
    reconnect_count: int
    bytes_sent: int
    bytes_received: int
    metadata: Dict[str, Any]
    created_at: str


class KeepaliveTCPClient:
    def __init__(self, config: TCPClientConfig):
        self.config = config
        self.client_id = str(uuid.uuid4())
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.last_heartbeat: Optional[str] = None
        self.reconnect_count = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._reconnect_thread: Optional[threading.Thread] = None
        self._state_path = Path.home() / f".qb_protocol_tcp_client_{self.client_id[:8]}.json"
        self._load_state()

    def _load_state(self):
        if self._state_path.exists():
            try:
                with open(self._state_path, "r") as f:
                    data = json.load(f)
                    self.reconnect_count = data.get("reconnect_count", 0)
                    self.bytes_sent = data.get("bytes_sent", 0)
                    self.bytes_received = data.get("bytes_received", 0)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open(self._state_path, "w") as f:
                json.dump({
                    "client_id": self.client_id,
                    "host": self.config.host,
                    "port": self.config.port,
                    "connected": self.connected,
                    "last_heartbeat": self.last_heartbeat,
                    "reconnect_count": self.reconnect_count,
                    "bytes_sent": self.bytes_sent,
                    "bytes_received": self.bytes_received,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def connect(self) -> bool:
        with self._lock:
            if self.connected and self.sock:
                try:
                    self.sock.send(b"")
                    return True
                except Exception:
                    self.connected = False
                    self.sock = None

            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.config.timeout)

                if hasattr(socket, 'TCP_KEEPIDLE'):
                    self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, self.config.keepalive_idle)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, self.config.keepalive_interval)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, self.config.keepalive_count)

                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                self.sock.connect((self.config.host, self.config.port))
                self.connected = True
                self.last_heartbeat = datetime.utcnow().isoformat() + "Z"
                self._save_state()
                LOG.info(f"TCP client connected to {self.config.host}:{self.config.port}")
                return True

            except Exception as e:
                LOG.warning(f"TCP client connection failed: {e}")
                self.connected = False
                self.sock = None
                self._save_state()
                return False

    def disconnect(self) -> None:
        with self._lock:
            self._stop_event.set()
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
            self.connected = False
            self._save_state()

    def send(self, data: bytes) -> bool:
        with self._lock:
            if not self.connected or not self.sock:
                if self.config.reconnect:
                    self._reconnect()
                if not self.connected:
                    return False

            try:
                self.sock.sendall(data)
                self.bytes_sent += len(data)
                self.last_heartbeat = datetime.utcnow().isoformat() + "Z"
                self._save_state()
                return True
            except Exception as e:
                LOG.warning(f"TCP client send failed: {e}")
                self.connected = False
                self.sock = None
                self._save_state()
                if self.config.reconnect:
                    self._reconnect()
                return False

    def receive(self, buffer_size: int = 4096) -> bytes:
        with self._lock:
            if not self.connected or not self.sock:
                return b""

            try:
                data = self.sock.recv(buffer_size)
                if data:
                    self.bytes_received += len(data)
                    self.last_heartbeat = datetime.utcnow().isoformat() + "Z"
                    self._save_state()
                return data
            except socket.timeout:
                return b""
            except Exception as e:
                LOG.warning(f"TCP client receive failed: {e}")
                self.connected = False
                self.sock = None
                self._save_state()
                if self.config.reconnect:
                    self._reconnect()
                return b""

    def _reconnect(self) -> None:
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        def _do_reconnect():
            if self.reconnect_count >= self.config.max_reconnect_attempts:
                LOG.error("TCP client max reconnect attempts reached")
                return

            backoff = self.config.reconnect_backoff * (2 ** min(self.reconnect_count, 10))
            time.sleep(backoff)

            with self._lock:
                self.reconnect_count += 1

            if self.connect():
                with self._lock:
                    self.reconnect_count = 0
                LOG.info(f"TCP client reconnected after {self.reconnect_count} attempts")

        self._reconnect_thread = threading.Thread(target=_do_reconnect, daemon=True)
        self._reconnect_thread.start()

    def start_heartbeat(self, interval: float = 30.0) -> None:
        self._stop_event.clear()

        def _heartbeat_loop():
            while not self._stop_event.is_set():
                try:
                    if self.connected:
                        self.send(b"\x00")
                    else:
                        if self.config.reconnect:
                            self.connect()
                except Exception as e:
                    LOG.warning(f"TCP heartbeat error: {e}")
                finally:
                    self._stop_event.wait(interval)

        self._heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "client_id": self.client_id,
                "host": self.config.host,
                "port": self.config.port,
                "connected": self.connected,
                "last_heartbeat": self.last_heartbeat,
                "reconnect_count": self.reconnect_count,
                "bytes_sent": self.bytes_sent,
                "bytes_received": self.bytes_received,
                "keepalive_idle": self.config.keepalive_idle,
                "keepalive_interval": self.config.keepalive_interval,
                "keepalive_count": self.config.keepalive_count,
            }


class KeepaliveTCPClientManager:
    def __init__(self):
        self.clients: Dict[str, KeepaliveTCPClient] = {}
        self._lock = threading.RLock()

    def create_client(self, host: str, port: int, **kwargs) -> KeepaliveTCPClient:
        config = TCPClientConfig(host=host, port=port, **kwargs)
        client = KeepaliveTCPClient(config)
        with self._lock:
            self.clients[client.client_id] = client
        return client

    def get_client(self, client_id: str) -> Optional[KeepaliveTCPClient]:
        with self._lock:
            return self.clients.get(client_id)

    def connect_all(self) -> Dict[str, bool]:
        results = {}
        with self._lock:
            for client_id, client in self.clients.items():
                results[client_id] = client.connect()
        return results

    def disconnect_all(self) -> None:
        with self._lock:
            for client in self.clients.values():
                client.disconnect()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            clients_status = {}
            for client_id, client in self.clients.items():
                clients_status[client_id] = client.get_state()
            return {
                "total_clients": len(self.clients),
                "connected_clients": sum(1 for c in self.clients.values() if c.connected),
                "clients": clients_status,
            }


keepalive_tcp_manager = KeepaliveTCPClientManager()

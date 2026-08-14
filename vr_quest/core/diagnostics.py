#!/usr/bin/env python3
"""
QB Protocol - VR Quest Network Diagnostics
Connection tests, packet loss, latency measurement.
"""

import os
import time
import uuid
import json
import logging
import threading
import socket
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.vr_quest.diagnostics")


@dataclass
class DiagnosticResult:
    test_id: str
    test_name: str
    status: str
    latency_ms: float
    packet_loss: float
    details: Dict[str, Any]
    timestamp: str


class NetworkDiagnostics:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_vr_diagnostics.json"):
        self.state_path = state_path
        self.results: List[DiagnosticResult] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.results = [DiagnosticResult(**r) for r in data.get("results", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "results": [asdict(r) for r in self.results[-500:]]
                }, f, indent=2, default=str)
        except Exception:
            pass

    def test_latency(self, host: str, port: int = 443, count: int = 10) -> DiagnosticResult:
        latencies = []
        for _ in range(count):
            try:
                start = time.time()
                sock = socket.create_connection((host, port), timeout=5)
                sock.close()
                latencies.append((time.time() - start) * 1000)
            except Exception:
                pass
            time.sleep(0.1)

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        packet_loss = (1 - len(latencies) / count) * 100

        result = DiagnosticResult(
            test_id=str(uuid.uuid4()),
            test_name="latency_test",
            status="passed" if avg_latency < 200 else "degraded",
            latency_ms=round(avg_latency, 2),
            packet_loss=round(packet_loss, 2),
            details={"host": host, "port": port, "samples": len(latencies)},
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.results.append(result)
            if len(self.results) > 500:
                self.results = self.results[-500:]
        self._save()
        return result

    def test_connection(self, url: str) -> DiagnosticResult:
        start = time.time()
        try:
            response = requests.get(url, timeout=10)
            latency = (time.time() - start) * 1000
            status = "passed" if response.status_code == 200 else "failed"
        except Exception as e:
            latency = (time.time() - start) * 1000
            status = "failed"
            response = None

        result = DiagnosticResult(
            test_id=str(uuid.uuid4()),
            test_name="connection_test",
            status=status,
            latency_ms=round(latency, 2),
            packet_loss=0.0,
            details={"url": url, "status_code": response.status_code if response else 0},
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.results.append(result)
            if len(self.results) > 500:
                self.results = self.results[-500:]
        self._save()
        return result

    def get_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self.results[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            recent = self.results[-10:]
            avg_latency = sum(r.latency_ms for r in recent) / len(recent) if recent else 0
            avg_packet_loss = sum(r.packet_loss for r in recent) / len(recent) if recent else 0
            return {
                "total_tests": len(self.results),
                "recent_avg_latency_ms": round(avg_latency, 2),
                "recent_avg_packet_loss": round(avg_packet_loss, 2),
            }


network_diagnostics = NetworkDiagnostics()

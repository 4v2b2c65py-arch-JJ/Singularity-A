#!/usr/bin/env python3
"""
QB Protocol - Python SDK
Quick connect, no-login, geolocation matching, instance management.
"""

import requests
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:17760"


class QBProtocolClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")

    def status(self) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/status").json()

    def health(self) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/health").json()

    def create_instance(self, name: str, platform: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/instances", json={"name": name, "platform": platform, "metadata": metadata}).json()

    def start_instance(self, instance_id: str) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/instances/{instance_id}/start").json()

    def stop_instance(self, instance_id: str) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/instances/{instance_id}/stop").json()

    def register_core(self, instance_id: str, core_type: str, thread_id: Optional[int] = None) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/cores", json={"instance_id": instance_id, "core_type": core_type, "thread_id": thread_id}).json()

    def core_heartbeat(self, core_id: str, load: float = 0.0, temperature: float = 0.0) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/cores/{core_id}/heartbeat", params={"load": load, "temperature": temperature}).json()

    def create_dream_layer(self, depth: float, projection: Dict[str, Any], convergence: float = 0.0, brain_state_emission: float = 0.0, singularity_threshold: float = 0.0) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/dream/layers", json={"depth": depth, "projection": projection, "convergence": convergence, "brain_state_emission": brain_state_emission, "singularity_threshold": singularity_threshold}).json()

    def dream_status(self) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/dream/status").json()

    def stabilizer_status(self) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/stabilizer/status").json()

    def ip_lookup(self, ip: Optional[str] = None, provider: str = "ip-api") -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/ip/lookup", json={"ip": ip, "provider": provider}).json()

    def quick_ip(self) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/ip/quick-connect").json()

    def trigger_regen(self) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/healing/regen").json()

    def healing_status(self) -> Dict[str, Any]:
        return requests.get(f"{self.base_url}/healing/status").json()

    def monitor_integrate(self, mirror_url: str) -> Dict[str, Any]:
        return requests.post(f"{self.base_url}/monitor/integrate", params={"mirror_url": mirror_url}).json()


client = QBProtocolClient()

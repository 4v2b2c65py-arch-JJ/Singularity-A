#!/usr/bin/env python3
"""
QB Protocol - Node Service Package
Accessible device node service package with rate limiting and import management.
"""

import time
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict

try:
    from qb_protocol.core.daemon import daemon
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon


@dataclass
class RateLimitRule:
    rule_id: str
    scope: str
    max_calls: int
    window_seconds: int
    burst: int
    active: bool = True


@dataclass
class ImportTicket:
    ticket_id: str
    source: str
    target_instance_id: str
    status: str
    created_at: str
    metadata: Dict[str, Any]


class RateLimiter:
    def __init__(self):
        self.windows: Dict[str, List[float]] = defaultdict(list)
        self.rules: Dict[str, RateLimitRule] = {}
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            RateLimitRule(rule_id="default-global", scope="global", max_calls=1000, window_seconds=60, burst=50),
            RateLimitRule(rule_id="instance-default", scope="instance", max_calls=200, window_seconds=60, burst=20),
            RateLimitRule(rule_id="dream-engine", scope="dream_engine", max_calls=500, window_seconds=60, burst=30),
        ]
        for rule in defaults:
            self.rules[rule.rule_id] = rule

    def allow(self, scope: str, cost: int = 1) -> bool:
        rule = self.rules.get(f"{scope}-default") or self.rules.get("default-global")
        if not rule or not rule.active:
            return True
        now = time.time()
        window_key = f"{scope}:{rule.rule_id}"
        timestamps = self.windows[window_key]
        cutoff = now - rule.window_seconds
        self.windows[window_key] = [t for t in timestamps if t > cutoff]
        if len(self.windows[window_key]) + cost > rule.max_calls:
            return False
        for _ in range(cost):
            self.windows[window_key].append(now)
        return True

    def add_rule(self, rule: RateLimitRule):
        self.rules[rule.rule_id] = rule


rate_limiter = RateLimiter()


class NodeServicePackage:
    def __init__(self):
        self.import_tickets: Dict[str, ImportTicket] = {}
        self.services: Dict[str, Callable] = {}

    def register_service(self, name: str, handler: Callable):
        self.services[name] = handler

    def create_import_ticket(self, source: str, target_instance_id: str, metadata: Optional[Dict[str, Any]] = None) -> ImportTicket:
        ticket = ImportTicket(
            ticket_id=str(uuid.uuid4()),
            source=source,
            target_instance_id=target_instance_id,
            status="queued",
            created_at=datetime.utcnow().isoformat() + "Z",
            metadata=metadata or {},
        )
        self.import_tickets[ticket.ticket_id] = ticket
        return ticket

    def dispatch(self, service_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not rate_limiter.allow(service_name):
            return {"status": "error", "error": "rate_limited", "service": service_name}
        handler = self.services.get(service_name)
        if not handler:
            return {"status": "error", "error": f"Unknown service: {service_name}"}
        try:
            result = handler(payload)
            return {"status": "ok", "service": service_name, "data": result}
        except Exception as e:
            return {"status": "error", "service": service_name, "error": str(e)}


node_package = NodeServicePackage()

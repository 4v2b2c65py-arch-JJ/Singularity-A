#!/usr/bin/env python3
"""
QB Protocol - Entry Gate & Signature Agent
Validates entry code, checks signatures, and manages agent identity.
"""

import hashlib
import hmac
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from qb_protocol.core.daemon import daemon
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.daemon import daemon

ENTRY_DB_FILE = Path(__file__).resolve().parent.parent / "qb_protocol_entries.json"


@dataclass
class EntryCredential:
    entry_code: str
    signature: str
    agent_id: str
    issued_at: str
    expires_at: str
    metadata: Dict[str, Any]


class EntryGate:
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or "qb-protocol-default-entry-secret"
        self.credentials: Dict[str, EntryCredential] = {}
        self._load()

    def _load(self):
        if ENTRY_DB_FILE.exists():
            import json
            with open(ENTRY_DB_FILE, "r") as f:
                data = json.load(f)
                for code, cd in data.get("credentials", {}).items():
                    self.credentials[code] = EntryCredential(**cd)

    def _save(self):
        import json
        with open(ENTRY_DB_FILE, "w") as f:
            json.dump({"credentials": {code: asdict(c) for code, c in self.credentials.items()}}, f, indent=2)

    def _sign(self, payload: str) -> str:
        return hmac.new(self.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]

    def issue_entry(self, agent_id: str, ttl_seconds: int = 3600, metadata: Optional[Dict[str, Any]] = None) -> EntryCredential:
        entry_code = hashlib.sha256(f"{agent_id}{time.time()}".encode()).hexdigest()[:24]
        now = datetime.utcnow().isoformat() + "Z"
        expires = datetime.utcnow().fromtimestamp(time.time() + ttl_seconds).isoformat() + "Z"
        signature = self._sign(f"{entry_code}:{agent_id}:{now}")
        cred = EntryCredential(
            entry_code=entry_code,
            signature=signature,
            agent_id=agent_id,
            issued_at=now,
            expires_at=expires,
            metadata=metadata or {},
        )
        self.credentials[entry_code] = cred
        self._save()
        return cred

    def validate_entry(self, entry_code: str, signature: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        cred = self.credentials.get(entry_code)
        if not cred:
            return {"valid": False, "reason": "unknown_entry_code"}
        expected = self._sign(f"{entry_code}:{cred.agent_id}:{cred.issued_at}")
        if not hmac.compare_digest(expected, signature):
            return {"valid": False, "reason": "invalid_signature"}
        if datetime.utcnow().isoformat() + "Z" > cred.expires_at:
            return {"valid": False, "reason": "expired"}
        if agent_id and agent_id != cred.agent_id:
            return {"valid": False, "reason": "agent_id_mismatch"}
        return {"valid": True, "agent_id": cred.agent_id, "entry_code": entry_code}

    def revoke_entry(self, entry_code: str) -> bool:
        if entry_code in self.credentials:
            del self.credentials[entry_code]
            self._save()
            return True
        return False


entry_gate = EntryGate()

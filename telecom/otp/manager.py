#!/usr/bin/env python3
"""
QB Protocol - OTP Manager
One-time passcode generation, rate limiting, and verification.
"""

import os
import time
import uuid
import json
import logging
import threading
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.telecom.otp")


@dataclass
class OTPCode:
    code_id: str
    phone: str
    code_hash: str
    attempt_count: int
    max_attempts: int
    expires_at: str
    used: bool
    metadata: Dict[str, Any]
    created_at: str


class OTPManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_telecom_otp.json"):
        self.state_path = state_path
        self.codes: Dict[str, OTPCode] = {}
        self.rate_limits: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for cid, c in data.get("codes", {}).items():
                        self.codes[cid] = OTPCode(**c)
                    self.rate_limits = data.get("rate_limits", {})
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "codes": {cid: asdict(c) for cid, c in self.codes.items()},
                    "rate_limits": self.rate_limits,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def _check_rate_limit(self, phone: str, max_per_minute: int = 5) -> bool:
        now = time.time()
        with self._lock:
            timestamps = self.rate_limits.get(phone, [])
            recent = [t for t in timestamps if now - t < 60]
            self.rate_limits[phone] = recent
            return len(recent) < max_per_minute

    def _record_otp_attempt(self, phone: str) -> None:
        now = time.time()
        with self._lock:
            timestamps = self.rate_limits.get(phone, [])
            timestamps.append(now)
            self.rate_limits[phone] = timestamps[-100:]
        self._save()

    def generate(self, phone: str, ttl_seconds: int = 300, max_attempts: int = 3) -> OTPCode:
        if not self._check_rate_limit(phone):
            raise ValueError("Rate limit exceeded")

        code = f"{secrets.randbelow(10000):04d}"
        now = datetime.utcnow()
        expires = now.replace(microsecond=0).isoformat() + "Z"
        otp = OTPCode(
            code_id=str(uuid.uuid4()),
            phone=phone,
            code_hash=hashlib.sha256(code.encode()).hexdigest(),
            attempt_count=0,
            max_attempts=max_attempts,
            expires_at=expires,
            used=False,
            metadata={"ttl_seconds": ttl_seconds},
            created_at=now.isoformat() + "Z",
        )
        with self._lock:
            self.codes[otp.code_id] = otp
        self._record_otp_attempt(phone)
        self._save()
        return otp

    def verify(self, phone: str, code: str) -> Dict[str, Any]:
        with self._lock:
            for otp in self.codes.values():
                if otp.phone == phone and not otp.used:
                    if otp.code_hash == hashlib.sha256(code.encode()).hexdigest():
                        otp.used = True
                        self._save()
                        return {"status": "valid", "code_id": otp.code_id}
                    otp.attempt_count += 1
                    if otp.attempt_count >= otp.max_attempts:
                        otp.used = True
                        self._save()
                        return {"status": "blocked", "reason": "max_attempts_exceeded"}
        self._save()
        return {"status": "invalid"}

    def get_codes(self, phone: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            codes = list(self.codes.values())
            if phone:
                codes = [c for c in codes if c.phone == phone]
            return [asdict(c) for c in codes]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            active = len([c for c in self.codes.values() if not c.used])
            return {
                "total_codes": len(self.codes),
                "active_codes": active,
                "rate_limited_phones": len(self.rate_limits),
            }


otp_manager = OTPManager()

#!/usr/bin/env python3
"""
QB Protocol - Telecom Privacy Architecture
Privacy-focused message handling and data retention.
"""

import os
import time
import uuid
import json
import logging
import threading
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.telecom.privacy")


@dataclass
class PrivacyConfig:
    store_phone_encrypted: bool
    hash_phone_for_lookup: bool
    sms_content_retention_seconds: int
    delete_account_enabled: bool
    passkey_primary: bool
    sms_fallback_only: bool
    metadata: Dict[str, Any]


class PrivacyManager:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_telecom_privacy.json"):
        self.state_path = state_path
        self.config = PrivacyConfig(
            store_phone_encrypted=True,
            hash_phone_for_lookup=True,
            sms_content_retention_seconds=86400,
            delete_account_enabled=True,
            passkey_primary=True,
            sms_fallback_only=True,
            metadata={},
        )
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.config = PrivacyConfig(**data.get("config", asdict(self.config)))
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({"config": asdict(self.config)}, f, indent=2, default=str)
        except Exception:
            pass

    def hash_phone(self, phone: str) -> str:
        return hashlib.sha256(phone.encode()).hexdigest()

    def mask_phone(self, phone: str) -> str:
        if len(phone) <= 8:
            return "****"
        return f"{phone[:4]}...{phone[-4:]}"

    def update_config(self, **kwargs) -> PrivacyConfig:
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        self._save()
        return self.config

    def get_config(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self.config)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "config": asdict(self.config),
                "retention_hours": round(self.config.sms_content_retention_seconds / 3600, 1),
            }


privacy_manager = PrivacyManager()

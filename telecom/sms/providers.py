#!/usr/bin/env python3
"""
QB Protocol - SMS Providers
Multi-provider SMS adapter with failover support.
"""

import os
import time
import uuid
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from abc import ABC, abstractmethod

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.telecom.sms")


@dataclass
class SMSMessage:
    message_id: str
    to: str
    from_number: str
    text: str
    provider: str
    status: str
    metadata: Dict[str, Any]
    sent_at: str


class SMSProvider(ABC):
    @abstractmethod
    def send(self, to: str, text: str, from_number: Optional[str] = None) -> SMSMessage:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class TelnyxProvider(SMSProvider):
    def __init__(self, api_key: str, from_number: str):
        self.api_key = api_key
        self.from_number = from_number
        self.sent = 0

    def send(self, to: str, text: str, from_number: Optional[str] = None) -> SMSMessage:
        self.sent += 1
        return SMSMessage(
            message_id=str(uuid.uuid4()),
            to=to,
            from_number=from_number or self.from_number,
            text=text,
            provider="telnyx",
            status="sent",
            metadata={"simulated": True},
            sent_at=datetime.utcnow().isoformat() + "Z",
        )

    def get_status(self) -> Dict[str, Any]:
        return {"provider": "telnyx", "sent": self.sent}


class VonageProvider(SMSProvider):
    def __init__(self, api_key: str, api_secret: str, from_name: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.from_name = from_name
        self.sent = 0

    def send(self, to: str, text: str, from_number: Optional[str] = None) -> SMSMessage:
        self.sent += 1
        return SMSMessage(
            message_id=str(uuid.uuid4()),
            to=to,
            from_number=from_number or self.from_name,
            text=text,
            provider="vonage",
            status="sent",
            metadata={"simulated": True},
            sent_at=datetime.utcnow().isoformat() + "Z",
        )

    def get_status(self) -> Dict[str, Any]:
        return {"provider": "vonage", "sent": self.sent}


class SinchProvider(SMSProvider):
    def __init__(self, api_key: str, api_secret: str, from_number: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.from_number = from_number
        self.sent = 0

    def send(self, to: str, text: str, from_number: Optional[str] = None) -> SMSMessage:
        self.sent += 1
        return SMSMessage(
            message_id=str(uuid.uuid4()),
            to=to,
            from_number=from_number or self.from_number,
            text=text,
            provider="sinch",
            status="sent",
            metadata={"simulated": True},
            sent_at=datetime.utcnow().isoformat() + "Z",
        )

    def get_status(self) -> Dict[str, Any]:
        return {"provider": "sinch", "sent": self.sent}


class SMSAdapter:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent.parent / "qb_protocol_telecom_sms.json"):
        self.state_path = state_path
        self.providers: Dict[str, SMSProvider] = {}
        self.messages: List[SMSMessage] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self.messages = [SMSMessage(**m) for m in data.get("messages", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "messages": [asdict(m) for m in self.messages[-1000:]]
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_provider(self, name: str, provider: SMSProvider) -> None:
        with self._lock:
            self.providers[name] = provider

    def send_sms(self, to: str, text: str, provider_name: Optional[str] = None, from_number: Optional[str] = None) -> SMSMessage:
        providers = list(self.providers.values())
        if not providers:
            return SMSMessage(
                message_id=str(uuid.uuid4()),
                to=to,
                from_number="",
                text=text,
                provider="none",
                status="failed",
                metadata={"error": "no_providers_configured"},
                sent_at=datetime.utcnow().isoformat() + "Z",
            )

        if provider_name and provider_name in self.providers:
            provider = self.providers[provider_name]
        else:
            provider = providers[0]

        try:
            message = provider.send(to, text, from_number)
            with self._lock:
                self.messages.append(message)
                if len(self.messages) > 1000:
                    self.messages = self.messages[-1000:]
            self._save()
            return message
        except Exception as e:
            return SMSMessage(
                message_id=str(uuid.uuid4()),
                to=to,
                from_number="",
                text=text,
                provider=provider_name or "unknown",
                status="failed",
                metadata={"error": str(e)},
                sent_at=datetime.utcnow().isoformat() + "Z",
            )

    def get_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(m) for m in self.messages[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_providers": len(self.providers),
                "provider_names": list(self.providers.keys()),
                "total_messages": len(self.messages),
            }


sms_adapter = SMSAdapter()

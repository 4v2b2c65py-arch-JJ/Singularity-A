#!/usr/bin/env python3
"""
QB Protocol - Message Log
Stores messages, requests, invoices, and conversations with full metadata.
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
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.communication.message_log")


class MessageType(Enum):
    MESSAGE = "message"
    REQUEST = "request"
    INVOICE = "invoice"
    CONVERSATION = "conversation"
    SYSTEM = "system"


@dataclass
class MessageRecord:
    message_id: str
    conversation_id: str
    message_type: str
    sender: str
    recipient: str
    content: Dict[str, Any]
    coordinates: Dict[str, Any]
    timestamp: str
    heartbeat: str
    status: str
    metadata: Dict[str, Any]


class MessageLog:
    def __init__(self, db_path: Path = Path(__file__).resolve().parent.parent / "qb_protocol_messages.json"):
        self.db_path = db_path
        self.messages: List[MessageRecord] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    self.messages = [MessageRecord(**m) for m in data.get("messages", [])]
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump({
                    "messages": [asdict(m) for m in self.messages[-10000:]]
                }, f, indent=2, default=str)
        except Exception:
            pass

    def record(self, conversation_id: str, message_type: MessageType, sender: str, recipient: str, content: Dict[str, Any], coordinates: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> MessageRecord:
        now = datetime.utcnow().isoformat() + "Z"
        record = MessageRecord(
            message_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            message_type=message_type.value,
            sender=sender,
            recipient=recipient,
            content=content,
            coordinates=coordinates,
            timestamp=now,
            heartbeat=now,
            status="sent",
            metadata=metadata or {},
        )
        with self._lock:
            self.messages.append(record)
            if len(self.messages) > 10000:
                self.messages = self.messages[-10000:]
        self._save()
        return record

    def get_conversation(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            conv = [m for m in self.messages if m.conversation_id == conversation_id]
            return [asdict(m) for m in conv[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_messages": len(self.messages),
                "conversation_count": len(set(m.conversation_id for m in self.messages)),
            }


message_log = MessageLog()

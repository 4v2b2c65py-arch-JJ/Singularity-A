#!/usr/bin/env python3
"""
QB Protocol - Communication Timeline Manager
Manages past, present, and future timelines for conversations.
Only one timeline active at a time per conversation.
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

LOG = logging.getLogger("qb_protocol.communication.timeline")


class TimelineMode(Enum):
    PAST = "past"
    PRESENT = "present"
    FUTURE = "future"


@dataclass
class TimelineEntry:
    entry_id: str
    conversation_id: str
    mode: str
    content: Dict[str, Any]
    timestamp: str
    coordinates: Dict[str, Any]
    user_info: Dict[str, Any]
    metadata: Dict[str, Any]


class CommunicationTimeline:
    def __init__(self, db_path: Path = Path(__file__).resolve().parent.parent / "qb_protocol_timeline.json"):
        self.db_path = db_path
        self.timelines: Dict[str, List[TimelineEntry]] = {}
        self.active_mode: Dict[str, str] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    for conv_id, entries in data.get("timelines", {}).items():
                        self.timelines[conv_id] = [TimelineEntry(**e) for e in entries]
                    self.active_mode = data.get("active_mode", {})
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump({
                    "timelines": {
                        conv_id: [asdict(e) for e in entries[-1000:]]
                        for conv_id, entries in self.timelines.items()
                    },
                    "active_mode": self.active_mode,
                }, f, indent=2, default=str)
        except Exception:
            pass

    def record(self, conversation_id: str, mode: TimelineMode, content: Dict[str, Any], coordinates: Dict[str, Any], user_info: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> TimelineEntry:
        entry = TimelineEntry(
            entry_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            mode=mode.value,
            content=content,
            timestamp=datetime.utcnow().isoformat() + "Z",
            coordinates=coordinates,
            user_info=user_info,
            metadata=metadata or {},
        )
        with self._lock:
            if conversation_id not in self.timelines:
                self.timelines[conversation_id] = []
            self.timelines[conversation_id].append(entry)
            if len(self.timelines[conversation_id]) > 10000:
                self.timelines[conversation_id] = self.timelines[conversation_id][-10000:]
            self.active_mode[conversation_id] = mode.value
        self._save()
        return entry

    def get_timeline(self, conversation_id: str, mode: Optional[TimelineMode] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            entries = self.timelines.get(conversation_id, [])
            if mode:
                entries = [e for e in entries if e.mode == mode.value]
            return [asdict(e) for e in entries[-limit:]]

    def set_active_mode(self, conversation_id: str, mode: "TimelineMode | str") -> Dict[str, Any]:
        if isinstance(mode, str):
            mode = TimelineMode(mode)
        with self._lock:
            self.active_mode[conversation_id] = mode.value
        self._save()
        return {"conversation_id": conversation_id, "active_mode": mode.value}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_conversations": len(self.timelines),
                "active_modes": self.active_mode,
                "total_entries": sum(len(entries) for entries in self.timelines.values()),
            }


communication_timeline = CommunicationTimeline()

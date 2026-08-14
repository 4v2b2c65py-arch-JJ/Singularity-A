#!/usr/bin/env python3
"""
QB Protocol - Stream Mapper
AI-powered stream selection and mapping engine.
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

LOG = logging.getLogger("qb_protocol.streaming.stream_mapper")


@dataclass
class StreamMapping:
    mapping_id: str
    item_id: str
    realm_id: str
    layer_id: str
    selected_source_id: str
    alternative_sources: List[str]
    confidence: float
    reason: str
    metadata: Dict[str, Any]
    mapped_at: str


class StreamMapper:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent / "qb_protocol_streaming_mappings.json"):
        self.state_path = state_path
        self.mappings: Dict[str, StreamMapping] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for mid, m in data.get("mappings", {}).items():
                        self.mappings[mid] = StreamMapping(**m)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "mappings": {mid: asdict(m) for mid, m in self.mappings.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def select_stream(self, item_id: str, realm_id: str, layer_id: str, available_sources: List[str], preferences: Optional[Dict[str, Any]] = None) -> StreamMapping:
        if not available_sources:
            return StreamMapping(
                mapping_id=str(uuid.uuid4()),
                item_id=item_id,
                realm_id=realm_id,
                layer_id=layer_id,
                selected_source_id="",
                alternative_sources=[],
                confidence=0.0,
                reason="no_sources_available",
                metadata=preferences or {},
                mapped_at=datetime.utcnow().isoformat() + "Z",
            )

        preferred_quality = (preferences or {}).get("quality", "any")
        preferred_language = (preferences or {}).get("language", "en")

        scored = []
        for source_id in available_sources:
            score = 0.5
            if "4k" in source_id or "uhd" in source_id:
                score += 0.3
            if "1080p" in source_id or "1080" in source_id:
                score += 0.2
            if "720p" in source_id or "720" in source_id:
                score += 0.1
            scored.append((source_id, min(score, 1.0)))

        scored.sort(key=lambda x: x[1], reverse=True)
        selected_id = scored[0][0]
        alternatives = [s[0] for s in scored[1:]]

        mapping = StreamMapping(
            mapping_id=str(uuid.uuid4()),
            item_id=item_id,
            realm_id=realm_id,
            layer_id=layer_id,
            selected_source_id=selected_id,
            alternative_sources=alternatives,
            confidence=scored[0][1],
            reason="ai_quality_selection",
            metadata=preferences or {},
            mapped_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.mappings[mapping.mapping_id] = mapping
        self._save()
        return mapping

    def get_mapping(self, item_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for m in self.mappings.values():
                if m.item_id == item_id:
                    return asdict(m)
        return None

    def get_mappings(self, realm_id: str, layer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            mappings = [m for m in self.mappings.values() if m.realm_id == realm_id]
            if layer_id:
                mappings = [m for m in mappings if m.layer_id == layer_id]
            return [asdict(m) for m in mappings]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_mappings": len(self.mappings),
            }


stream_mapper = StreamMapper()

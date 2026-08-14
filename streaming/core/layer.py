#!/usr/bin/env python3
"""
QB Protocol - Layer Detection
Automatic layer detection for streaming realms (surface, deep, core, unknown).
"""

import os
import time
import uuid
import json
import logging
import threading
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.streaming.layer")


@dataclass
class DetectedLayer:
    layer_id: str
    realm_id: str
    name: str
    layer_type: str
    depth: int
    confidence: float
    indicators: List[str]
    metadata: Dict[str, Any]
    detected_at: str


class LayerDetector:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent.parent / "qb_protocol_streaming_layers.json"):
        self.state_path = state_path
        self.layers: Dict[str, DetectedLayer] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for lid, l in data.get("layers", {}).items():
                        self.layers[lid] = DetectedLayer(**l)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "layers": {lid: asdict(l) for lid, l in self.layers.items()}
                }, f, indent=2, default=str)
        except Exception:
            pass

    def detect_layer(self, realm_id: str, name: str, url: str, description: str = "") -> DetectedLayer:
        name_lower = name.lower()
        url_lower = url.lower()
        desc_lower = description.lower()
        text = f"{name_lower} {url_lower} {desc_lower}"

        indicators = []
        depth = 0
        confidence = 0.0
        layer_type = "unknown"

        surface_patterns = ["popular", "trending", "new", "latest", "top", "recommended", "home", "main"]
        deep_patterns = ["classic", "old", "archive", "rare", "cult", "obscure", "hidden", "deep"]
        core_patterns = ["4k", "uhd", "remux", "blu-ray", "remaster", "original", "core", "master"]

        for pattern in surface_patterns:
            if pattern in text:
                indicators.append(pattern)
                confidence += 0.2
                depth = max(depth, 0)

        for pattern in deep_patterns:
            if pattern in text:
                indicators.append(pattern)
                confidence += 0.2
                depth = max(depth, 1)

        for pattern in core_patterns:
            if pattern in text:
                indicators.append(pattern)
                confidence += 0.25
                depth = max(depth, 2)

        if confidence >= 0.3:
            if any(p in indicators for p in core_patterns):
                layer_type = "core"
            elif any(p in indicators for p in deep_patterns):
                layer_type = "deep"
            elif any(p in indicators for p in surface_patterns):
                layer_type = "surface"
        else:
            layer_type = "unknown"

        layer = DetectedLayer(
            layer_id=str(uuid.uuid4()),
            realm_id=realm_id,
            name=name,
            layer_type=layer_type,
            depth=depth,
            confidence=min(confidence, 1.0),
            indicators=list(set(indicators)),
            metadata={"url": url, "description": description},
            detected_at=datetime.utcnow().isoformat() + "Z",
        )
        with self._lock:
            self.layers[layer.layer_id] = layer
        self._save()
        return layer

    def get_layers(self, realm_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(l) for l in self.layers.values() if l.realm_id == realm_id]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            types = {}
            for l in self.layers.values():
                types[l.layer_type] = types.get(l.layer_type, 0) + 1
            return {
                "total_layers": len(self.layers),
                "types": types,
            }


layer_detector = LayerDetector()

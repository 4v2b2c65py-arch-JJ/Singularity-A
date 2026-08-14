#!/usr/bin/env python3
"""
QB Protocol - Celestial Router
Detects new dimensions and routes connections across the multiverse.
Handles dimensional coordinates, heartbeat monitoring, and data translation.
"""

import os
import time
import uuid
import json
import logging
import threading
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOG = logging.getLogger("qb_protocol.celestial_router")


class DimensionStatus(Enum):
    CONNECTED = "connected"
    PENDING = "pending"
    UNSTABLE = "unstable"
    LOST = "lost"


class TranslationStatus(Enum):
    MATCHED = "matched"
    PARTIAL = "partial"
    UNMATCHED = "unmatched"
    TRANSLATED = "translated"


@dataclass
class DimensionalCoordinate:
    dimension_id: str
    name: str
    coordinates: Dict[str, float]
    universe: str
    timestamp: str
    stability: float
    connections: List[str]
    metadata: Dict[str, Any]


@dataclass
class Heartbeat:
    connection_id: str
    dimension_id: str
    timestamp: str
    latency_ms: float
    status: str
    metadata: Dict[str, Any]


@dataclass
class DataTranslation:
    translation_id: str
    source_dimension: str
    target_dimension: str
    source_data: Dict[str, Any]
    target_data: Dict[str, Any]
    status: str
    confidence: float
    metadata: Dict[str, Any]


class CelestialRouter:
    def __init__(self, state_path: Path = Path(__file__).resolve().parent.parent / "qb_protocol_celestial.json"):
        self.state_path = state_path
        self.dimensions: Dict[str, DimensionalCoordinate] = {}
        self.heartbeats: Dict[str, Heartbeat] = {}
        self.translations: List[DataTranslation] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    for did, d in data.get("dimensions", {}).items():
                        self.dimensions[did] = DimensionalCoordinate(**d)
                    for cid, h in data.get("heartbeats", {}).items():
                        self.heartbeats[cid] = Heartbeat(**h)
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.state_path, "w") as f:
                json.dump({
                    "dimensions": {did: asdict(d) for did, d in self.dimensions.items()},
                    "heartbeats": {cid: asdict(h) for cid, h in self.heartbeats.items()},
                    "translations": [asdict(t) for t in self.translations[-1000:]],
                }, f, indent=2, default=str)
        except Exception:
            pass

    def register_dimension(self, name: str, coordinates: Dict[str, float], universe: str = "earth", stability: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> DimensionalCoordinate:
        dimension = DimensionalCoordinate(
            dimension_id=str(uuid.uuid4()),
            name=name,
            coordinates=coordinates,
            universe=universe,
            timestamp=datetime.utcnow().isoformat() + "Z",
            stability=stability,
            connections=[],
            metadata=metadata or {},
        )
        with self._lock:
            self.dimensions[dimension.dimension_id] = dimension
        self._save()
        return dimension

    def route_connection(self, source_dimension: str, target_dimension: str) -> Dict[str, Any]:
        with self._lock:
            source = self.dimensions.get(source_dimension)
            target = self.dimensions.get(target_dimension)
            if not source or not target:
                return {"status": DimensionStatus.LOST.value, "message": "Dimension not found"}
            source.connections.append(target_dimension)
            target.connections.append(source_dimension)
            self._save()
            return {
                "status": DimensionStatus.CONNECTED.value,
                "source": source_dimension,
                "target": target_dimension,
                "stability": min(source.stability, target.stability),
            }

    def record_heartbeat(self, connection_id: str, dimension_id: str, latency_ms: float, status: str = "ok") -> Heartbeat:
        heartbeat = Heartbeat(
            connection_id=connection_id,
            dimension_id=dimension_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            latency_ms=latency_ms,
            status=status,
            metadata={},
        )
        with self._lock:
            self.heartbeats[connection_id] = heartbeat
        self._save()
        return heartbeat

    def translate_data(self, source_dimension: str, target_dimension: str, data: Dict[str, Any]) -> DataTranslation:
        translated = self._translate_dimension_data(data, source_dimension, target_dimension)
        translation = DataTranslation(
            translation_id=str(uuid.uuid4()),
            source_dimension=source_dimension,
            target_dimension=target_dimension,
            source_data=data,
            target_data=translated,
            status=TranslationStatus.TRANSLATED.value,
            confidence=0.95,
            metadata={},
        )
        with self._lock:
            self.translations.append(translation)
            if len(self.translations) > 1000:
                self.translations = self.translations[-1000:]
        self._save()
        return translation

    def _translate_dimension_data(self, data: Dict[str, Any], source: str, target: str) -> Dict[str, Any]:
        translated = {}
        for key, value in data.items():
            if isinstance(value, str):
                translated[key] = f"[{target}] {value}"
            elif isinstance(value, dict):
                translated[key] = self._translate_dimension_data(value, source, target)
            elif isinstance(value, list):
                translated[key] = [self._translate_dimension_data(item, source, target) if isinstance(item, dict) else item for item in value]
            else:
                translated[key] = value
        return translated

    def compare_world_data(self, world_data: Dict[str, Any], dimension_data: Dict[str, Any]) -> Dict[str, Any]:
        world_keys = set(world_data.keys())
        dimension_keys = set(dimension_data.keys())
        common_keys = world_keys & dimension_keys
        return {
            "world_keys": list(world_keys),
            "dimension_keys": list(dimension_keys),
            "common_keys": list(common_keys),
            "world_only": list(world_keys - dimension_keys),
            "dimension_only": list(dimension_keys - world_keys),
            "match_ratio": len(common_keys) / max(len(world_keys | dimension_keys), 1),
        }

    def get_dimensions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [asdict(d) for d in self.dimensions.values()]

    def get_dimension(self, dimension_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            dim = self.dimensions.get(dimension_id)
            return asdict(dim) if dim else None

    def get_connections(self) -> List[Dict[str, Any]]:
        with self._lock:
            connections = []
            for dim_id, dim in self.dimensions.items():
                for conn in dim.connections:
                    connections.append({"from": dim_id, "to": conn, "dimension_name": dim.name})
            return connections

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_dimensions": len(self.dimensions),
                "total_connections": sum(len(d.connections) for d in self.dimensions.values()) // 2,
                "total_heartbeats": len(self.heartbeats),
                "total_translations": len(self.translations),
                "dimensions": list(self.dimensions.keys()),
            }


celestial_router = CelestialRouter()
